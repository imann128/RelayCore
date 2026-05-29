from django.urls import path
from .views import ReceiveWebhookView

app_name = 'delivery'

urlpatterns = [
    path('receive/<slug:source_slug>/', ReceiveWebhookView.as_view(), name='receive'),
]
