"""Resolve per-user portal access (role defaults + admin overrides)."""
from accounts.portal_modules import PORTAL_MODULES, default_access_for_role


def get_user_permission_overrides(user):
    if not user.is_authenticated:
        return {}
    return {
        p.module: p.is_allowed
        for p in user.portal_permission_overrides.all()
    }


def user_can_access(user, module_code):
    """Check if user may access a portal module."""
    if not user.is_authenticated:
        return False
    if module_code not in PORTAL_MODULES:
        return False

    overrides = get_user_permission_overrides(user)
    if module_code in overrides:
        return overrides[module_code]

    return default_access_for_role(user.role, module_code)


def get_user_access_map(user):
    """Full module access map for templates."""
    if not user.is_authenticated:
        return {}
    overrides = get_user_permission_overrides(user)
    result = {}
    for code in PORTAL_MODULES:
        if code in overrides:
            result[code] = overrides[code]
        else:
            result[code] = default_access_for_role(user.role, code)
    return result


def set_user_permissions(user, permissions_dict, granted_by=None):
    """Bulk set permission overrides. permissions_dict: {module: is_allowed}"""
    from accounts.models import UserPortalPermission

    for module, is_allowed in permissions_dict.items():
        if module not in PORTAL_MODULES:
            continue
        default = default_access_for_role(user.role, module)
        if is_allowed == default:
            UserPortalPermission.objects.filter(user=user, module=module).delete()
        else:
            UserPortalPermission.objects.update_or_create(
                user=user,
                module=module,
                defaults={'is_allowed': is_allowed, 'granted_by': granted_by},
            )