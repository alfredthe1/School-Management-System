"""Production settings — PostgreSQL, WhiteNoise, HTTPS, structured logging."""
import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False

_secret = os.environ.get('DJANGO_SECRET_KEY', '')
if not _secret or _secret.startswith('django-insecure') or _secret == 'change-me-to-a-long-random-string':
    raise ImproperlyConfigured('Set a strong DJANGO_SECRET_KEY in production.')
SECRET_KEY = _secret

if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['localhost', '127.0.0.1']:
    raise ImproperlyConfigured('Set DJANGO_ALLOWED_HOSTS to your domain(s) in production.')

if not CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured('Set DJANGO_CSRF_TRUSTED_ORIGINS to your HTTPS origin(s).')

if MOBILE_MONEY_ENABLED and not MOBILE_MONEY_CALLBACK_SECRET:
    raise ImproperlyConfigured(
        'Set MOBILE_MONEY_CALLBACK_SECRET when mobile money is enabled in production.'
    )

# --- Database: PostgreSQL (recommended) ---
_db_engine = os.environ.get('DJANGO_DB_ENGINE', 'postgresql').lower()
if _db_engine == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / os.environ.get('SQLITE_PATH', 'db.sqlite3'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('POSTGRES_DB', 'happy_child_school'),
            'USER': os.environ.get('POSTGRES_USER', 'happy_child'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
            'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
            'CONN_MAX_AGE': int(os.environ.get('POSTGRES_CONN_MAX_AGE', '60')),
            'OPTIONS': {
                'sslmode': os.environ.get('POSTGRES_SSLMODE', 'prefer'),
            },
        }
    }

# --- Static files via WhiteNoise ---
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# --- HTTPS / cookies ---
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True').lower() in ('1', 'true', 'yes')
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
USE_X_FORWARDED_HOST = os.environ.get('USE_X_FORWARDED_HOST', 'True').lower() in ('1', 'true', 'yes')
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if os.environ.get('ENABLE_PROXY_MIDDLEWARE', '').lower() in ('1', 'true', 'yes'):
    MIDDLEWARE.append('school.middleware.ProxyMiddleware')

# --- Cache (use Redis in multi-worker setups via REDIS_URL) ---
_redis_url = os.environ.get('REDIS_URL', '')
if _redis_url:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': _redis_url,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

# --- Logging ---
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'django.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': os.environ.get('LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'django.security': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}