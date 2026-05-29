from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('webhooks/', include('apps.delivery.urls')),
    path('dashboard/', include('apps.monitoring.urls')),
    path('api/', include('apps.api.urls')),
]
