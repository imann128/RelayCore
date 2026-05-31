"""
Django settings for relaycore project.

Sensitive values are read from environment variables (or a .env file via
python-decouple). Never hard-code secrets here.
"""

from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# Security
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'django_celery_beat',
    'rest_framework',
    'corsheaders',
    'auditlog',
    'axes',

    # Project apps
    'apps.core',
    'apps.delivery',
    'apps.routing',
    'apps.idempotency',
    'apps.transformers',
    'apps.monitoring',
    'apps.api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',          # must be first
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'auditlog.middleware.AuditlogMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
]

ROOT_URLCONF = 'relaycore.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'relaycore.wsgi.application'

# Database — PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME':     config('DB_NAME',     default='relaycore'),
        'USER':     config('DB_USER',     default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST':     config('DB_HOST',     default='localhost'),
        'PORT':     config('DB_PORT',     default='5432'),
    }
}

# Cache — Redis (also used for idempotency SET NX)
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
    }
}

# Celery
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Celery Beat uses the DB-backed scheduler from django-celery-beat
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# During pytest runs, execute tasks synchronously in the same process.
# This lets e2e tests assert on delivery outcomes without a real Celery worker.
import sys
if 'pytest' in sys.modules:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Webhook delivery settings
WEBHOOK_IDEMPOTENCY_TTL_HOURS = config('WEBHOOK_IDEMPOTENCY_TTL_HOURS', default=24, cast=int)
WEBHOOK_DELIVERY_TIMEOUT_SECONDS = config('WEBHOOK_DELIVERY_TIMEOUT_SECONDS', default=30, cast=int)
WEBHOOK_MAX_RETRIES = 5

# Celery Beat — static periodic task schedule
#
# django-celery-beat's DatabaseScheduler merges these with any PeriodicTask
# rows in the DB. Defining here ensures collect_metrics runs even before
# anyone has added rows via Django admin.
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'collect-metrics-every-60s': {
        'task': 'apps.delivery.tasks.collect_metrics',
        'schedule': 60.0,   # seconds — equivalent to crontab(minute='*') but simpler
    },
}

# Field encryption (django-fernet-fields)
#
# Used to encrypt Destination.auth_header at rest.
# Generate a key with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
#
# IMPORTANT: If this key is lost or rotated without re-encrypting existing
# rows, all stored auth_header values become unreadable. Back it up securely.
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY', default='')

# Sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 86400 * 7   # 7 days

# CSRF — React dev server needs to read the cookie
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost:5173,http://127.0.0.1:5173',
    cast=Csv(),
)

# CORS — allow the Vite dev server to talk to Django
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:5173,http://127.0.0.1:5173',
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

# Authentication backends — axes must be first
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Axes — brute-force login protection
AXES_FAILURE_LIMIT = 5                      # lock after 5 failed attempts
AXES_COOLOFF_TIME = 1                       # unlock after 1 hour
AXES_RESET_ON_SUCCESS = True                # reset failure count on successful login
AXES_LOCKOUT_PARAMETERS = ['username']      # track by username — avoids proxy IP mismatch behind nginx
AXES_USERNAME_FORM_FIELD = 'username'

# HTTPS enforcement (active in production when DEBUG=False)
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG