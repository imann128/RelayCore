from __future__ import annotations

from rest_framework import serializers
from auditlog.models import LogEntry

from apps.core.models import Destination, MetricPoint, Route, Source, WebhookDelivery
from apps.transformers.choices import TRANSFORMER_CHOICES


class SourceSerializer(serializers.ModelSerializer):
    secret = serializers.CharField(
        write_only=True, required=False, allow_blank=True,
        help_text='HMAC secret. Write-only.',
    )

    class Meta:
        model = Source
        fields = [
            'id', 'name', 'slug', 'secret', 'signature_scheme',
            'rate_limit_per_minute', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class DestinationSerializer(serializers.ModelSerializer):
    auth_header = serializers.CharField(
        write_only=True, required=False, allow_blank=True,
        help_text='Authorization header value. Write-only; stored encrypted.',
    )

    class Meta:
        model = Destination
        fields = ['id', 'name', 'url', 'auth_header', 'timeout_seconds', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_url(self, value):
        from apps.core.validators import validate_destination_url
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_destination_url(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message)
        return value


class RouteSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)
    destination_name = serializers.CharField(source='destination.name', read_only=True)
    transformer_class_display = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = [
            'id', 'source', 'source_name', 'event_type', 'condition',
            'destination', 'destination_name', 'transformer_class',
            'transformer_class_display', 'priority', 'is_active', 'rate_limit_per_minute',
        ]
        read_only_fields = ['id']

    def get_transformer_class_display(self, obj):
        return dict(TRANSFORMER_CHOICES).get(obj.transformer_class, obj.transformer_class)


class WebhookDeliverySerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)

    class Meta:
        model = WebhookDelivery
        fields = [
            'id', 'source', 'source_name', 'idempotency_key', 'event_type',
            'raw_payload', 'headers', 'status', 'attempt_count', 'last_error',
            'received_at', 'delivered_at',
        ]
        read_only_fields = [
            'id', 'source', 'source_name', 'idempotency_key', 'event_type',
            'raw_payload', 'headers', 'status', 'attempt_count', 'last_error',
            'received_at', 'delivered_at',
        ]


class MetricPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetricPoint
        fields = ['id', 'name', 'value', 'labels', 'timestamp']
        read_only_fields = ['id', 'name', 'value', 'labels', 'timestamp']


class AuditLogSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()
    action = serializers.SerializerMethodField()
    resource_type = serializers.SerializerMethodField()
    resource_repr = serializers.SerializerMethodField()

    class Meta:
        model = LogEntry
        fields = [
            'id', 'actor', 'action', 'resource_type', 'resource_repr',
            'object_id', 'changes', 'timestamp',
        ]

    def get_actor(self, obj):
        return obj.actor.username if obj.actor else 'system'

    def get_action(self, obj):
        return obj.get_action_display()

    def get_resource_type(self, obj):
        return obj.content_type.model if obj.content_type else ''

    def get_resource_repr(self, obj):
        return obj.object_repr
