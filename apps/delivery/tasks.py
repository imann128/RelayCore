"""
Celery tasks for webhook routing, delivery, and metric aggregation.

route_and_deliver — main delivery task with exponential backoff + DLQ
collect_metrics   — Celery Beat task, runs every 60s
"""

import logging
from datetime import timedelta

import httpx
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.conf import settings
from django.utils import timezone

from apps.core.models import WebhookDelivery, MetricPoint
from apps.routing.service import find_matching_routes
from apps.transformers.registry import get_transformer
from apps.delivery.ratelimit import is_rate_limited, route_rate_limit_key

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=getattr(settings, 'WEBHOOK_MAX_RETRIES', 5),
    default_retry_delay=1,
)
def route_and_deliver(self, delivery_id: int) -> None:
    """
    Route a WebhookDelivery to all matching destinations and deliver.

    Route-level rate limiting: if a route's per-minute limit is exceeded,
    that route is skipped for this delivery (logged as a warning). The
    overall task still succeeds — other matching routes are still delivered.
    This is intentional: a rate-limited route is not a transient failure
    worth retrying; it means too many events are hitting this specific route.

    Retry schedule (exponential backoff — 2^attempt seconds):
      Attempt 0 → fails → wait 1s  → attempt 1
      Attempt 1 → fails → wait 2s  → attempt 2
      Attempt 2 → fails → wait 4s  → attempt 3
      Attempt 3 → fails → wait 8s  → attempt 4
      Attempt 4 → fails → wait 16s → attempt 5
      Attempt 5 → fails → dead letter queue
    """
    try:
        delivery = WebhookDelivery.objects.select_related('source').get(pk=delivery_id)
    except WebhookDelivery.DoesNotExist:
        logger.error("route_and_deliver: delivery %s not found", delivery_id)
        return

    try:
        matching_routes = find_matching_routes(
            delivery.source,
            delivery.event_type,
            delivery.raw_payload,
        )

        if not matching_routes:
            logger.info(
                "No matching routes for delivery %s (source=%s event=%s)",
                delivery_id, delivery.source, delivery.event_type
            )
            delivery.status = 'delivered'
            delivery.delivered_at = timezone.now()
            delivery.save(update_fields=['status', 'delivered_at'])
            return

        for route in matching_routes:
            # Route-level rate limit check.
            # Route.rate_limit_per_minute overrides Source default if set.
            route_limit = route.rate_limit_per_minute or delivery.source.rate_limit_per_minute
            rl_key = route_rate_limit_key(route.pk)

            if is_rate_limited(rl_key, limit=route_limit):
                logger.warning(
                    "Route %s rate limit exceeded (%s/min) — skipping for delivery %s",
                    route.pk, route_limit, delivery_id
                )
                continue

            transformer_class = get_transformer(route.transformer_class)
            transformed_payload = transformer_class().transform(delivery.raw_payload)
            _post_to_destination(route.destination, transformed_payload)

            logger.info(
                "Delivered delivery %s via route %s to %s",
                delivery_id, route.pk, route.destination.url
            )

        delivery.status = 'delivered'
        delivery.delivered_at = timezone.now()
        delivery.save(update_fields=['status', 'delivered_at'])

    except Exception as exc:
        delivery.attempt_count += 1
        delivery.last_error = str(exc)
        delivery.status = 'retrying'
        delivery.save(update_fields=['attempt_count', 'last_error', 'status'])

        logger.warning(
            "Delivery %s failed (attempt %s): %s — scheduling retry",
            delivery_id, delivery.attempt_count, exc
        )

        try:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        except MaxRetriesExceededError:
            delivery.status = 'dead_lettered'
            delivery.save(update_fields=['status'])
            logger.error(
                "Delivery %s permanently failed after %s attempts — dead lettered. Last error: %s",
                delivery_id, delivery.attempt_count, delivery.last_error
            )


def _post_to_destination(destination, payload: dict) -> None:
    """
    HTTP POST the transformed payload to a destination URL.

    auth_header is stored encrypted on the model. The EncryptedCharField
    transparently decrypts on access — no extra steps here.
    """
    headers = {'Content-Type': 'application/json'}
    if destination.auth_header:
        headers['Authorization'] = destination.auth_header

    timeout = destination.timeout_seconds

    response = httpx.post(
        destination.url,
        json=payload,
        headers=headers,
        timeout=timeout,
    )
    response.raise_for_status()


# Celery Beat metric aggregation task

@shared_task
def collect_metrics() -> None:
    """
    Pre-aggregate key metrics and write MetricPoint rows every 60 seconds.
    """
    now = timezone.now()
    one_minute_ago = now - timedelta(seconds=60)

    from django.db.models import Count, Q

    agg = WebhookDelivery.objects.aggregate(
        total=Count('id'),
        delivered=Count('id', filter=Q(status='delivered')),
        in_queue=Count('id', filter=Q(status__in=['received', 'routed', 'retrying'])),
        dead_lettered=Count('id', filter=Q(status='dead_lettered')),
        duplicates=Count('id', filter=Q(status='duplicate')),
        sig_failed=Count('id', filter=Q(status='sig_failed')),
    )

    throughput = WebhookDelivery.objects.filter(received_at__gte=one_minute_ago).count()

    total = agg['total'] or 1
    success_rate = agg['delivered'] / total  # store as ratio 0.0–1.0; frontend multiplies by 100

    metrics = [
        ('webhook.success_rate',      success_rate,           {}),
        ('webhook.queue_depth',       agg['in_queue'],        {}),
        ('webhook.dead_letter_count', agg['dead_lettered'],   {}),
        ('webhook.throughput_1m',     throughput,             {}),
        ('webhook.duplicate_count',   agg['duplicates'],      {}),
        ('webhook.sig_failed_count',  agg['sig_failed'],      {}),
    ]

    MetricPoint.objects.bulk_create([
        MetricPoint(name=name, value=value, labels=labels)
        for name, value, labels in metrics
    ])

    logger.debug("collect_metrics: wrote %s MetricPoint rows", len(metrics))
