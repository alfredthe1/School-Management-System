"""Mobile money gateway readiness and runtime configuration."""
from django.conf import settings


def _mask(value, show=4):
    if not value:
        return ''
    if len(value) <= show:
        return '****'
    return f"{'*' * (len(value) - show)}{value[-show:]}"


def get_mtn_config():
    return {
        'env': getattr(settings, 'MTN_MOMO_ENV', 'sandbox'),
        'subscription_key': bool(getattr(settings, 'MTN_MOMO_SUBSCRIPTION_KEY', '')),
        'api_user': bool(getattr(settings, 'MTN_MOMO_API_USER', '')),
        'api_key': bool(getattr(settings, 'MTN_MOMO_API_KEY', '')),
        'callback_url': getattr(settings, 'MTN_MOMO_CALLBACK_URL', ''),
        'currency': getattr(settings, 'MTN_MOMO_CURRENCY', 'UGX'),
        'token_url': getattr(settings, 'MTN_MOMO_TOKEN_URL', ''),
        'request_url': getattr(settings, 'MTN_MOMO_REQUEST_URL', ''),
    }


def get_airtel_config():
    return {
        'client_id': bool(getattr(settings, 'AIRTEL_MONEY_CLIENT_ID', '')),
        'client_secret': bool(getattr(settings, 'AIRTEL_MONEY_CLIENT_SECRET', '')),
        'callback_url': getattr(settings, 'AIRTEL_MONEY_CALLBACK_URL', ''),
        'currency': getattr(settings, 'AIRTEL_MONEY_CURRENCY', 'UGX'),
        'token_url': getattr(settings, 'AIRTEL_MONEY_TOKEN_URL', ''),
        'collect_url': getattr(settings, 'AIRTEL_MONEY_COLLECT_URL', ''),
    }


def mtn_is_ready():
    cfg = get_mtn_config()
    return all([cfg['subscription_key'], cfg['api_user'], cfg['api_key'], cfg['callback_url']])


def airtel_is_ready():
    cfg = get_airtel_config()
    return all([cfg['client_id'], cfg['client_secret'], cfg['callback_url']])


def callback_security_ready():
    secret = getattr(settings, 'MOBILE_MONEY_CALLBACK_SECRET', '')
    return bool(secret) or settings.DEBUG


def get_payment_gateway_status():
    """Full readiness report for admin dashboard and parent portal."""
    mtn = get_mtn_config()
    airtel = get_airtel_config()
    mtn_ready = mtn_is_ready()
    airtel_ready = airtel_is_ready()
    simulation = not (mtn_ready or airtel_ready)
    enabled = getattr(settings, 'MOBILE_MONEY_ENABLED', True)

    mtn_checklist = [
        {'label': 'Subscription key', 'ok': mtn['subscription_key'], 'env': 'MTN_MOMO_SUBSCRIPTION_KEY'},
        {'label': 'API user', 'ok': mtn['api_user'], 'env': 'MTN_MOMO_API_USER'},
        {'label': 'API key', 'ok': mtn['api_key'], 'env': 'MTN_MOMO_API_KEY'},
        {'label': 'Callback URL', 'ok': bool(mtn['callback_url']), 'env': 'MTN_MOMO_CALLBACK_URL'},
    ]
    airtel_checklist = [
        {'label': 'Client ID', 'ok': airtel['client_id'], 'env': 'AIRTEL_MONEY_CLIENT_ID'},
        {'label': 'Client secret', 'ok': airtel['client_secret'], 'env': 'AIRTEL_MONEY_CLIENT_SECRET'},
        {'label': 'Callback URL', 'ok': bool(airtel['callback_url']), 'env': 'AIRTEL_MONEY_CALLBACK_URL'},
    ]

    return {
        'enabled': enabled,
        'simulation_mode': simulation,
        'live_mode': not simulation and enabled,
        'mtn_ready': mtn_ready,
        'airtel_ready': airtel_ready,
        'mtn_checklist': mtn_checklist,
        'airtel_checklist': airtel_checklist,
        'callback_secret_set': bool(getattr(settings, 'MOBILE_MONEY_CALLBACK_SECRET', '')),
        'callback_security_ok': callback_security_ready(),
        'min_amount': getattr(settings, 'MOBILE_MONEY_MIN_AMOUNT', 500),
        'max_amount': getattr(settings, 'MOBILE_MONEY_MAX_AMOUNT', 10_000_000),
    }