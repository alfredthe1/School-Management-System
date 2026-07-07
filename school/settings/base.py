"""
Shared Django settings for Happy Child Nursery and Primary School.
Environment-specific overrides live in development.py and production.py.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env from project root when python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_filters',
    # School apps
    'accounts',
    'core',
    'students',
    'teachers',
    'academics',
    'examinations',
    'fees',
    'communication',
    'reports',
    'parents',
    'announcements',
    'logs',
    'staff',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'school.middleware.SecurityHeadersMiddleware',
    'school.middleware.ActivityLogMiddleware',
]

ROOT_URLCONF = 'school.urls'
WSGI_APPLICATION = 'school.wsgi.application'

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
                'core.context_processors.school_info',
                'core.context_processors.parent_sidebar',
                'core.context_processors.staff_nav',
                'communication.context_processors.notification_counts',
                'accounts.context_processors.portal_access',
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 10},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Kampala'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

AUTH_USER_MODEL = 'accounts.User'
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'core:dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Hosts (override in env-specific settings) ---
_hosts = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [h.strip() for h in _hosts.split(',') if h.strip()]

_csrf_origins = os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(',') if o.strip()]

# --- SMS (Twilio) ---
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')

# --- Mobile money ---
MOBILE_MONEY_ENABLED = os.environ.get('MOBILE_MONEY_ENABLED', 'True').lower() in ('1', 'true', 'yes')
MOBILE_MONEY_MIN_AMOUNT = int(os.environ.get('MOBILE_MONEY_MIN_AMOUNT', '500'))
MOBILE_MONEY_MAX_AMOUNT = int(os.environ.get('MOBILE_MONEY_MAX_AMOUNT', '10000000'))
MOBILE_MONEY_POLL_SECONDS = int(os.environ.get('MOBILE_MONEY_POLL_SECONDS', '3'))

MTN_MOMO_ENV = os.environ.get('MTN_MOMO_ENV', 'sandbox')
MTN_MOMO_SUBSCRIPTION_KEY = os.environ.get('MTN_MOMO_SUBSCRIPTION_KEY', '')
MTN_MOMO_API_USER = os.environ.get('MTN_MOMO_API_USER', '')
MTN_MOMO_API_KEY = os.environ.get('MTN_MOMO_API_KEY', '')
MTN_MOMO_CURRENCY = os.environ.get('MTN_MOMO_CURRENCY', 'UGX')
MTN_MOMO_CALLBACK_URL = os.environ.get(
    'MTN_MOMO_CALLBACK_URL', 'http://127.0.0.1:8000/parents/mobile-money/mtn/callback/'
)
MTN_MOMO_TOKEN_URL = os.environ.get(
    'MTN_MOMO_TOKEN_URL', 'https://sandbox.momodeveloper.mtn.com/collection/token/'
)
MTN_MOMO_REQUEST_URL = os.environ.get(
    'MTN_MOMO_REQUEST_URL', 'https://sandbox.momodeveloper.mtn.com/collection/v1_0/requesttopay'
)

AIRTEL_MONEY_CLIENT_ID = os.environ.get('AIRTEL_MONEY_CLIENT_ID', '')
AIRTEL_MONEY_CLIENT_SECRET = os.environ.get('AIRTEL_MONEY_CLIENT_SECRET', '')
AIRTEL_MONEY_CURRENCY = os.environ.get('AIRTEL_MONEY_CURRENCY', 'UGX')
AIRTEL_MONEY_CALLBACK_URL = os.environ.get(
    'AIRTEL_MONEY_CALLBACK_URL', 'http://127.0.0.1:8000/parents/mobile-money/airtel/callback/'
)
AIRTEL_MONEY_TOKEN_URL = os.environ.get(
    'AIRTEL_MONEY_TOKEN_URL', 'https://openapiuat.airtel.africa/auth/oauth2/token'
)
AIRTEL_MONEY_COLLECT_URL = os.environ.get(
    'AIRTEL_MONEY_COLLECT_URL', 'https://openapiuat.airtel.africa/merchant/v1/payments/'
)

MOBILE_MONEY_CALLBACK_SECRET = os.environ.get('MOBILE_MONEY_CALLBACK_SECRET', '')
MOBILE_MONEY_CALLBACK_HEADER = os.environ.get('MOBILE_MONEY_CALLBACK_HEADER', 'X-Callback-Secret')
_momo_ips = os.environ.get('MOBILE_MONEY_CALLBACK_IP_ALLOWLIST', '')
MOBILE_MONEY_CALLBACK_IP_ALLOWLIST = [ip.strip() for ip in _momo_ips.split(',') if ip.strip()]

# --- Email ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL', 'Happy Child Nursery and Primary School <noreply@happychild.ug>'
)

# --- CSRF & session ---
CSRF_FAILURE_VIEW = 'school.security.csrf_failure'
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_USE_SESSIONS = False
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 60 * 60 * 8
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

PROXY_TARGET_BASE = os.environ.get('PROXY_TARGET_BASE', '')

# Runtime directories (logs, collected static — not in git)
RUNTIME_DIR = BASE_DIR / 'runtime'
LOG_DIR = RUNTIME_DIR / 'logs'