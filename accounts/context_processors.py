from accounts.permission_utils import get_user_access_map, user_can_access


def portal_access(request):
    if not request.user.is_authenticated:
        return {}
    return {
        'portal_access': get_user_access_map(request.user),
        'user_can_access': lambda module: user_can_access(request.user, module),
    }