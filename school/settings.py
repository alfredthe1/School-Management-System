import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-!replace-this-with-random-key'
DEBUG = True

# -------------------------------------------------------------------
# ALLOWED_HOSTS – use hostnames only, no scheme/path
# -------------------------------------------------------------------
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'blend-skydiver-overlabor.ngrok-free.dev',   # your Ngrok tunnel
    '.ngrok.io',                # any *.ngrok.io
    '.ngrok.app',               # any *.ngrok.app
    '.ngrok-free.dev',          # any *.ngrok-free.dev
    '*',                      # ← keep commented for production; enable only for quick tests
]

# -------------------------------------------------------------------
# CSRF_TRUSTED_ORIGINS – must include scheme + host (no trailing slash)
# -------------------------------------------------------------------
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'https://blend-skydiver-overlabor.ngrok-free.dev',
    'https://*.ngrok-free.dev',
    'https://*.ngrok.io',
    'https://*.ngrok.app',
]

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
    # custom apps
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
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # The proxy middleware should run early to fix request scheme/host
    'school.middleware.ProxyMiddleware',         # ← moved up
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'school.middleware.ActivityLogMiddleware',
]

ROOT_URLCONF = 'school.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'school.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

AUTH_USER_MODEL = 'accounts.User'

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'core:dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -------------------------------------------------------------------
# Ngrok / proxy settings – essential for HTTPS & correct host headers
# -------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# Force secure cookies when behind HTTPS (Ngrok sets X-Forwarded-Proto: https)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Note: If you also need to test via plain http://localhost, comment out the two lines above.

# SMS (Twilio)
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')

# M-Pesa Daraja API
MPESA_ENV = os.environ.get('MPESA_ENV', 'sandbox')
MPESA_CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY', '')
MPESA_CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET', '')
MPESA_SHORTCODE = os.environ.get('MPESA_SHORTCODE', '')
MPESA_PASSKEY = os.environ.get('MPESA_PASSKEY', '')
MPESA_CALLBACK_URL = os.environ.get('MPESA_CALLBACK_URL', 'http://127.0.0.1:8000/parents/mpesa/callback/')

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'Happy Child School <noreply@happychild.ug>')