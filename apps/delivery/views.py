"""
Webhook ingestion endpoint.

POST /webhooks/receive/<source_slug>/

Deliberately thin — does the minimum synchronous work (verify, deduplicate,
rate-limit, persist) and immediately returns 200 to the sender. Heavy work
happens asynchronously in Celery.

Duplicates always return 200, never 4xx. A 4xx signals an error to the
provider and triggers retries, which is the opposite of what deduplication
is trying to achieve.
"""

import hashlib
import hmac
import json
import logging

from django.http import HttpRequest, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.core.models import Source, WebhookDelivery
from apps.idempotency.service import generate_idempotency_key, is_duplicate
from apps.delivery.ratelimit import is_rate_limited, source_rate_limit_key

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class ReceiveWebhookView(View):
    """
    Accepts inbound webhooks, verifies signature, rate-limits, deduplicates,
    and enqueues.

    Request lifecycle:
      1. Resolve source by slug
      2. Read raw body bytes
      3. Verify HMAC signature (if source requires it)
      4. Source-level rate limit check
      5. Idempotency check
      6. Extract provider-specific metadata headers into payload
      7. Persist WebhookDelivery row
      8. Enqueue Celery task, return 200 immediately
    """

    http_method_names = ['post']

    def post(self, request: HttpRequest, source_slug: str) -> JsonResponse:
        # Resolve source
        try:
            source = Source.objects.get(slug=source_slug, is_active=True)
        except Source.DoesNotExist:
            logger.warning("Webhook received for unknown/inactive slug: %s", source_slug)
            return JsonResponse({'error': 'Unknown source'}, status=404)

        raw_body: bytes = request.body

        # Signature verification
        if source.signature_scheme == 'github_hmac':
            if not self._verify_github_hmac(raw_body, source.secret, request):
                WebhookDelivery.objects.create(
                    source=source,
                    idempotency_key='sig_failed',
                    event_type=request.headers.get('X-GitHub-Event', ''),
                    raw_payload={},
                    headers=dict(request.headers),
                    status='sig_failed',
                )
                logger.warning("HMAC verification failed for source '%s'", source.name)
                return JsonResponse({'error': 'Invalid signature'}, status=401)

        # Source-level rate limit
        rl_key = source_rate_limit_key(source.slug)
        if is_rate_limited(rl_key, limit=source.rate_limit_per_minute):
            logger.warning(
                "Rate limit exceeded for source '%s' (%s/min)",
                source.name, source.rate_limit_per_minute
            )
            return JsonResponse(
                {'error': 'Rate limit exceeded'},
                status=429,
                headers={'Retry-After': '60'},
            )

        # Idempotency check
        delivery_header = request.headers.get('X-GitHub-Delivery', '')
        idem_key = generate_idempotency_key(source.name, delivery_header, raw_body)

        if is_duplicate(idem_key):
            logger.info("Duplicate webhook dropped: key=%s", idem_key)
            return JsonResponse({'status': 'duplicate'}, status=200)

        # Parse payload and inject provider metadata headers
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        payload = self._inject_provider_metadata(payload, request)
        event_type = request.headers.get('X-GitHub-Event', '')

        # Persist
        delivery = WebhookDelivery.objects.create(
            source=source,
            idempotency_key=idem_key,
            event_type=event_type,
            raw_payload=payload,
            headers=dict(request.headers),
            status='received',
        )

        # Enqueue and return
        delivery.status = 'routed'
        delivery.save(update_fields=['status'])

        from apps.delivery.tasks import route_and_deliver
        route_and_deliver.delay(delivery.pk)

        logger.info(
            "Webhook received and enqueued: source=%s event=%s delivery_id=%s",
            source.name, event_type, delivery.pk
        )
        return JsonResponse({'status': 'accepted', 'delivery_id': delivery.pk}, status=200)

    # Private helpers

    @staticmethod
    def _verify_github_hmac(raw_body: bytes, secret: str, request: HttpRequest) -> bool:
        """
        Verify GitHub's X-Hub-Signature-256 header.
        Uses hmac.compare_digest() instead of == to prevent timing attacks.
        """
        signature_header = request.headers.get('X-Hub-Signature-256', '')
        if not signature_header.startswith('sha256='):
            return False

        expected_sig = signature_header[len('sha256='):]
        actual_sig = hmac.new(
            key=secret.encode('utf-8'),
            msg=raw_body,
            digestmod=hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_sig, actual_sig)

    @staticmethod
    def _inject_provider_metadata(payload: dict, request: HttpRequest) -> dict:
        """
        Merge provider-specific metadata headers into the payload dict.

        Transformers only receive raw_payload, but some providers (Google
        Calendar) send important metadata in headers rather than the body.
        Merging headers into the payload before persisting lets transformers
        read them without querying the WebhookDelivery row.

        Each provider's metadata is nested under a private key (double
        underscore prefix) to avoid colliding with real payload fields.

        Handled:
          - Google Calendar: X-Goog-* headers -> payload['__goog_meta']
          - GitHub: X-GitHub-* headers -> payload['__github_meta']
        """
        payload = dict(payload)  # shallow copy — do not mutate the original

        goog_headers = {
            'channel_id':     request.headers.get('X-Goog-Channel-ID', ''),
            'resource_id':    request.headers.get('X-Goog-Resource-ID', ''),
            'resource_state': request.headers.get('X-Goog-Resource-State', ''),
            'resource_uri':   request.headers.get('X-Goog-Resource-URI', ''),
            'expiration':     request.headers.get('X-Goog-Channel-Expiration', ''),
        }
        if any(goog_headers.values()):
            payload['__goog_meta'] = goog_headers

        github_headers = {
            'delivery_id': request.headers.get('X-GitHub-Delivery', ''),
            'event':       request.headers.get('X-GitHub-Event', ''),
            'hook_id':     request.headers.get('X-GitHub-Hook-ID', ''),
        }
        if any(github_headers.values()):
            payload['__github_meta'] = github_headers

        return payload
