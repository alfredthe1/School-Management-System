"""
Settings entry point. Set DJANGO_ENV=production on the server.

  development (default) → SQLite, debug toolbar-friendly, ngrok/LAN helpers
  production            → PostgreSQL, WhiteNoise, HTTPS, strict secrets
"""
import os

_env = os.environ.get('DJANGO_ENV', 'development').lower().strip()

if _env == 'production':
    from .production import *  # noqa: F401,F403
else:
    from .development import *  # noqa: F401,F403