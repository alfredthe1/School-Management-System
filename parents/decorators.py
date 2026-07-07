from functools import wraps
from django.shortcuts import render, get_object_or_404
from students.models import Student
from accounts.permission_utils import user_can_access


def parent_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        if request.user.role != 'parent':
            return render(request, 'parents/not_authorized.html', status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def parent_module_required(module_code):
    """Parent role + dynamic portal permission for a module."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            if request.user.role != 'parent':
                return render(request, 'parents/not_authorized.html', status=403)
            if not user_can_access(request.user, module_code):
                return render(request, 'parents/not_authorized.html', status=403)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def get_parent_child(request, student_id):
    """Return a student only if it belongs to the logged-in parent."""
    return get_object_or_404(Student, id=student_id, parent=request.user, is_active=True)