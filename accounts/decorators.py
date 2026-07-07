from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect

from accounts.permission_utils import user_can_access


def admin_required(view_func):
    """Only system administrators may manage users."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if request.user.role != 'admin':
            messages.error(request, 'Only administrators can manage system users.')
            return redirect('core:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def portal_module_required(module_code):
    """Require access to a portal module (role default or user override)."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if not user_can_access(request.user, module_code):
                messages.error(request, 'You do not have permission to access this section.')
                return redirect('core:dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator