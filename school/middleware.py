"""Custom middleware: activity logging, optional proxy, security headers."""
import re

import requests
from django.conf import settings
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
from logs.models import UserAction

NGROK_ORIGIN_SUFFIXES = ('.ngrok-free.app', '.ngrok.io', '.ngrok.app')
LAN_ORIGIN_RE = re.compile(
    r'^https?://('
    r'192\.168\.\d{1,3}\.\d{1,3}|'
    r'10\.\d{1,3}\.\d{1,3}\.\d{1,3}|'
    r'172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}'
    r')(:\d+)?$'
)


def _is_dev_mobile_origin(origin):
    if not origin:
        return False
    if any(origin.endswith(suffix) for suffix in NGROK_ORIGIN_SUFFIXES):
        return True
    return bool(LAN_ORIGIN_RE.match(origin))


class NgrokCsrfOriginMiddleware:
    """DEBUG only: auto-trust ngrok and LAN origins so login/forms work on mobile."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.DEBUG:
            origin = request.META.get('HTTP_ORIGIN', '')
            if _is_dev_mobile_origin(origin) and origin not in settings.CSRF_TRUSTED_ORIGINS:
                settings.CSRF_TRUSTED_ORIGINS.append(origin)
        return self.get_response(request)

# Paths excluded from view-level activity logging (noise / static assets)
_ACTIVITY_LOG_SKIP = re.compile(
    r'^/(static|media|favicon\.ico|admin/js|admin/css)',
    re.I,
)


class SecurityHeadersMiddleware:
    """Add defense-in-depth HTTP headers on every response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not response.get('X-Content-Type-Options'):
            response['X-Content-Type-Options'] = 'nosniff'
        if not response.get('Referrer-Policy'):
            response['Referrer-Policy'] = getattr(
                settings, 'SECURE_REFERRER_POLICY', 'strict-origin-when-cross-origin'
            )
        if not settings.DEBUG and not response.get('Permissions-Policy'):
            response['Permissions-Policy'] = (
                'camera=(), microphone=(), geolocation=(), payment=()'
            )
        return response


class ActivityLogMiddleware:
    """Log meaningful user actions — not every page view."""

    MUTATING_METHODS = frozenset({'POST', 'PUT', 'PATCH', 'DELETE'})

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.user.is_authenticated:
            return response
        if _ACTIVITY_LOG_SKIP.match(request.path):
            return response
        if request.method not in self.MUTATING_METHODS:
            return response
        if response.status_code >= 400:
            return response

        action_map = {
            'POST': 'create',
            'PUT': 'update',
            'PATCH': 'update',
            'DELETE': 'delete',
        }
        UserAction.objects.create(
            user=request.user,
            action_type=action_map.get(request.method, 'update'),
            description=f'{request.method} {request.path}',
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        return response

    def get_client_ip(self, request):
        if getattr(settings, 'USE_X_FORWARDED_HOST', False):
            forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
            if forwarded:
                return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


class ProxyMiddleware(MiddlewareMixin):
    """
    Forwards requests with a '/proxy/' path prefix to an external URL.
    Disabled by default — enable only via ENABLE_PROXY_MIDDLEWARE=1 in settings.
    """

    PREFIX = '/proxy/'

    def process_request(self, request):
        if not request.path.startswith(self.PREFIX):
            return None

        target_base = getattr(settings, 'PROXY_TARGET_BASE', '')
        if not target_base:
            return HttpResponse('Proxy disabled', status=403)

        path_rest = request.path[len(self.PREFIX):]
        if not path_rest.startswith('/'):
            path_rest = '/' + path_rest
        target_url = f"{target_base.rstrip('/')}{path_rest}"

        if request.GET:
            target_url += '?' + request.GET.urlencode()

        headers = {key: value for key, value in request.headers.items()}
        headers.pop('Host', None)

        method = request.method.lower()
        body = request.body if request.body else None

        try:
            resp = requests.request(
                method,
                target_url,
                headers=headers,
                data=body,
                timeout=30,
            )
        except requests.RequestException as e:
            return HttpResponse('Proxy error', status=502)

        django_resp = HttpResponse(
            resp.content,
            status=resp.status_code,
            content_type=resp.headers.get('Content-Type'),
        )
        for key, value in resp.headers.items():
            if key.lower() not in ('content-length', 'content-type', 'transfer-encoding'):
                django_resp[key] = value

        return django_resp