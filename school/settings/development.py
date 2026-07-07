"""Local development settings."""
import os

from .base import *  # noqa: F403

DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('1', 'true', 'yes')

_secret = os.environ.get('DJANGO_SECRET_KEY', '')
if _secret:
    SECRET_KEY = _secret
elif DEBUG:
    SECRET_KEY = 'django-insecure-dev-only-change-before-production'
else:
    raise ValueError('DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is False')

if not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = [
        'http://localhost:8000',
        'http://127.0.0.1:8000',
    ]

# ngrok / same-Wi-Fi mobile testing
for _ngrok_host in ('.ngrok-free.app', '.ngrok.io', '.ngrok.app'):
    if _ngrok_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_ngrok_host)
_ngrok_url = os.environ.get('NGROK_URL', '').strip().rstrip('/')
if _ngrok_url and _ngrok_url not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(_ngrok_url)
_lan_host = os.environ.get('LAN_HOST', '').strip()
if _lan_host and _lan_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_lan_host)

# Insert ngrok CSRF helper before CsrfViewMiddleware
_csrf_index = MIDDLEWARE.index('django.middleware.csrf.CsrfViewMiddleware')
MIDDLEWARE.insert(_csrf_index, 'school.middleware.NgrokCsrfOriginMiddleware')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

SECURE_REFERRER_POLICY = 'same-origin'

if os.environ.get('ENABLE_PROXY_MIDDLEWARE', '').lower() in ('1', 'true', 'yes'):
    MIDDLEWARE.append('school.middleware.ProxyMiddleware')

EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend',
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}