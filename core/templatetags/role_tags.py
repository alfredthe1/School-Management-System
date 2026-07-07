from django import template
from accounts.permission_utils import user_can_access

register = template.Library()


@register.filter
def has_role(user, roles):
    """Check if user.role is in a comma-separated list of roles."""
    if not user or not user.is_authenticated:
        return False
    allowed = [r.strip() for r in roles.split(',')]
    return user.role in allowed


@register.simple_tag
def user_has_role(user, *roles):
    if not user or not user.is_authenticated:
        return False
    return user.role in roles


@register.filter
def can_access(user, module_code):
    """Dynamic portal permission check (role + per-user overrides)."""
    return user_can_access(user, module_code)