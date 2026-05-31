from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    AuditLogViewSet, DestinationViewSet, LoginView, LogoutView, MeView,
    MetricsView, RouteViewSet, SourceViewSet, WebhookDeliveryViewSet,
)

router = DefaultRouter()
router.register(r'sources',      SourceViewSet,          basename='source')
router.register(r'destinations', DestinationViewSet,     basename='destination')
router.register(r'routes',       RouteViewSet,           basename='route')
router.register(r'deliveries',   WebhookDeliveryViewSet, basename='delivery')
router.register(r'audit-log',    AuditLogViewSet,        basename='audit-log')

urlpatterns = [
    path('auth/login/',  LoginView.as_view(),  name='api-login'),
    path('auth/logout/', LogoutView.as_view(), name='api-logout'),
    path('auth/me/',     MeView.as_view(),     name='api-me'),
    path('metrics/',     MetricsView.as_view(), name='api-metrics'),
    path('', include(router.urls)),
]
