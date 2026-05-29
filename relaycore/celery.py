"""
Celery application bootstrap.

This module is imported by relaycore/__init__.py so that
@shared_task decorators across all apps resolve to this app instance.
"""

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'relaycore.settings')

app = Celery('relaycore')

# Load config from Django settings, namespaced under CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks.py in every INSTALLED_APP
app.autodiscover_tasks()
