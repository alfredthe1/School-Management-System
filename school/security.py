"""Security helpers: CSRF failure page, webhook verification, rate limiting."""
import hashlib
import hmac
import ipaddress
import time
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt


def csrf_failure(request, reason=''):
    """User-friendly 403 when CSRF validation fails."""
    return render(request, '403_csrf.html', {'reason': reason}, status=403)


def get_client_ip(request):
    """Return client IP, honoring X-Forwarded-For when behind a trusted proxy."""
    if getattr(settings, 'USE_X_FORWARDED_HOST', False):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _ip_allowed(ip_str, allowlist):
    if not allowlist:
        return True
    if not ip_str:
        return False
    try:
        client = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    for entry in allowlist:
        entry = entry.strip()
        if not entry:
            continue
        try:
            if '/' in entry:
                if client in ipaddress.ip_network(entry, strict=False):
                    return True
            elif client == ipaddress.ip_address(entry):
                return True
        except ValueError:
            continue
    return False


def verify_mobile_money_callback(request):
    """
    Validate inbound MTN/Airtel webhook requests.

    External providers cannot send Django CSRF tokens, so callbacks stay
    csrf_exempt but must pass shared-secret and optional IP checks.
    In DEBUG without a configured secret, callbacks are allowed with a warning.
    """
    secret = getattr(settings, 'MOBILE_MONEY_CALLBACK_SECRET', '')
    allowlist = getattr(settings, 'MOBILE_MONEY_CALLBACK_IP_ALLOWLIST', [])

    if secret:
        header_name = getattr(
            settings, 'MOBILE_MONEY_CALLBACK_HEADER', 'X-Callback-Secret'
        )
        provided = request.headers.get(header_name, '')
        if not hmac.compare_digest(provided, secret):
            return False

    if allowlist and not _ip_allowed(get_client_ip(request), allowlist):
        return False

    if not secret and settings.DEBUG:
        return True

    if not secret:
        return False

    return True


def rate_limit(key_prefix, limit=30, window_seconds=60):
    """Simple cache-based rate limiter decorator."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            ip = get_client_ip(request) or 'unknown'
            bucket = f'rl:{key_prefix}:{ip}'
            now = time.time()
            hits = cache.get(bucket, [])
            hits = [t for t in hits if now - t < window_seconds]
            if len(hits) >= limit:
                return JsonResponse({'error': 'Too many requests'}, status=429)
            hits.append(now)
            cache.set(bucket, hits, window_seconds)
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def mobile_money_callback_view(view_func):
    """
    Decorator for provider webhooks: CSRF exempt + secret/IP validation + rate limit.
    """
    view_func = csrf_exempt(view_func)
    view_func = rate_limit('mobile_money_callback', limit=60, window_seconds=60)(view_func)

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not verify_mobile_money_callback(request):
            return HttpResponseForbidden('Unauthorized callback')
        return view_func(request, *args, **kwargs)

    wrapper.csrf_exempt = True
    return wrapper


def hash_for_audit(value):
    """One-way hash for logging sensitive values without storing them."""
    return hashlib.sha256(str(value).encode()).hexdigest()[:16]