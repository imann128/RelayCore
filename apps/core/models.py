from django.db import models
from auditlog.registry import auditlog
from apps.core.fields import EncryptedCharField
from apps.core.validators import validate_destination_url


class Source(models.Model):
    """
    A registered webhook producer, e.g. 'GitHub Production'.

    Each source has its own URL slug, optional HMAC secret for signature
    verification, and a default rate limit. Routes reference sources via FK.
    """
    SIGNATURE_SCHEMES = [
        ('github_hmac', 'GitHub HMAC-SHA256'),
        ('none',        'No Verification'),
    ]

    name                  = models.CharField(max_length=100, unique=True)
    slug                  = models.SlugField(unique=True,
                                help_text='Used in the inbound URL: /webhooks/receive/<slug>/')
    secret                = models.CharField(max_length=255, blank=True,
                                help_text='HMAC secret — leave blank if signature_scheme is none')
    signature_scheme      = models.CharField(max_length=50, choices=SIGNATURE_SCHEMES, default='none')
    rate_limit_per_minute = models.IntegerField(default=100)
    is_active             = models.BooleanField(default=True)
    created_at            = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Destination(models.Model):
    """
    A registered webhook consumer, e.g. 'Slack #engineering'.

    auth_header is stored encrypted using Fernet symmetric encryption
    (django-fernet-fields). The plaintext value is only ever held in memory
    during the Celery delivery task; it is never written to the DB in plaintext.

    Requires FIELD_ENCRYPTION_KEY in settings (set via FIELD_ENCRYPTION_KEY
    environment variable). Generate a key with:
      python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    """
    name            = models.CharField(max_length=100)
    url             = models.URLField()
    auth_header     = EncryptedCharField(max_length=500, blank=True,
                          help_text='Authorization header value — stored encrypted at rest')
    timeout_seconds = models.IntegerField(default=30)
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    def clean(self):
        validate_destination_url(self.url)

    def __str__(self):
        return f"{self.name} ({self.url})"


class Route(models.Model):
    """
    Maps a source + optional conditions to a destination + transformer.

    Routes are evaluated in priority order (lower number = first).
    All active routes matching a delivery are executed (fan-out, not first-match-wins).
    """
    from apps.transformers.choices import TRANSFORMER_CHOICES

    source                = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='routes')
    event_type            = models.CharField(max_length=100, db_index=True, blank=True,
                                help_text='Header-based filter, e.g. X-GitHub-Event value. Empty = match all.')
    condition             = models.JSONField(default=dict, blank=True,
                                help_text='JSONPath conditions dict, e.g. {"ref": "refs/heads/main"}')
    destination           = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name='routes')
    transformer_class     = models.CharField(max_length=200, choices=TRANSFORMER_CHOICES)
    priority              = models.IntegerField(default=0,
                                help_text='Lower number = evaluated first. Ties broken by pk.')
    is_active             = models.BooleanField(default=True)
    rate_limit_per_minute = models.IntegerField(null=True, blank=True,
                                help_text='Overrides source default if set')

    class Meta:
        ordering = ['priority', 'pk']
        indexes = [
            models.Index(fields=['source', 'event_type', 'is_active', 'priority']),
        ]

    def __str__(self):
        return f"{self.source} → {self.destination} via {self.transformer_class}"


class WebhookDelivery(models.Model):
    """
    Immutable log of every inbound webhook event.

    Status transitions:
      received → routed → delivered
      received → duplicate (dropped)
      received → sig_failed (dropped)
      routed   → retrying → delivered
      retrying → dead_lettered
    """
    STATUS_CHOICES = [
        ('received',      'Received'),
        ('duplicate',     'Duplicate — Dropped'),
        ('sig_failed',    'Signature Verification Failed'),
        ('routed',        'Routed to Queue'),
        ('delivered',     'Delivered'),
        ('retrying',      'Retrying'),
        ('dead_lettered', 'Dead Lettered'),
    ]

    source          = models.ForeignKey(Source, on_delete=models.SET_NULL, null=True, related_name='deliveries')
    idempotency_key = models.CharField(max_length=255, db_index=True)
    event_type      = models.CharField(max_length=100, blank=True)
    raw_payload     = models.JSONField()
    headers         = models.JSONField(default=dict)
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='received')
    attempt_count   = models.IntegerField(default=0)
    last_error      = models.TextField(blank=True)
    received_at     = models.DateTimeField(auto_now_add=True)
    delivered_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['source', 'status', 'received_at']),
            models.Index(fields=['idempotency_key']),
        ]

    def __str__(self):
        return f"Delivery {self.pk} [{self.status}] from {self.source}"


class MetricPoint(models.Model):
    """
    Pre-aggregated metrics written by Celery Beat every 60 seconds.
    """
    name      = models.CharField(max_length=100, db_index=True)
    value     = models.FloatField()
    labels    = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['name', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.name}={self.value} @ {self.timestamp}"


auditlog.register(Source)
auditlog.register(Destination, exclude_fields=['auth_header'])
auditlog.register(Route)
