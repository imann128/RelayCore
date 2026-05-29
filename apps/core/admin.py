from django.contrib import admin
from .models import Source, Destination, Route, WebhookDelivery, MetricPoint


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display  = ('name', 'slug', 'signature_scheme', 'rate_limit_per_minute', 'is_active', 'created_at')
    list_filter   = ('signature_scheme', 'is_active')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display  = ('name', 'url', 'timeout_seconds', 'is_active', 'created_at')
    list_filter   = ('is_active',)
    search_fields = ('name', 'url')


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display  = ('source', 'event_type', 'destination', 'transformer_class', 'priority', 'is_active')
    list_filter   = ('is_active', 'source', 'transformer_class')
    search_fields = ('event_type',)
    ordering      = ('priority',)


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display  = ('pk', 'source', 'event_type', 'status', 'attempt_count', 'received_at', 'delivered_at')
    list_filter   = ('status', 'source')
    search_fields = ('idempotency_key', 'event_type')
    readonly_fields = (
        'source', 'idempotency_key', 'event_type', 'raw_payload',
        'headers', 'status', 'attempt_count', 'last_error',
        'received_at', 'delivered_at',
    )

    def has_add_permission(self, request):
        # Deliveries are created by the system, not manually.
        return False


@admin.register(MetricPoint)
class MetricPointAdmin(admin.ModelAdmin):
    list_display  = ('name', 'value', 'labels', 'timestamp')
    list_filter   = ('name',)
    readonly_fields = ('name', 'value', 'labels', 'timestamp')

    def has_add_permission(self, request):
        return False
