"""Admin portal: manage system users (all roles)."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from accounts.permission_utils import get_user_access_map, set_user_permissions
from accounts.portal_modules import CATEGORIES, PORTAL_MODULES, default_access_for_role
from .decorators import admin_required
from .forms import AdminPasswordResetForm, SystemUserCreateForm, SystemUserEditForm, UserPermissionsForm

User = get_user_model()

ROLE_ICONS = {
    'admin': 'bi-shield-lock-fill',
    'headteacher': 'bi-mortarboard-fill',
    'teacher': 'bi-person-badge-fill',
    'bursar': 'bi-cash-stack',
    'parent': 'bi-people-fill',
}


@login_required
@admin_required
def user_list(request):
    users = User.objects.all().order_by('role', 'username')
    role = request.GET.get('role', '')
    status = request.GET.get('status', '')
    search = request.GET.get('search', '').strip()

    if role:
        users = users.filter(role=role)
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)
    if search:
        users = users.filter(
            Q(username__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
        )

    role_counts = {choice[0]: User.objects.filter(role=choice[0]).count() for choice in User.ROLE_CHOICES}

    return render(request, 'accounts/users/user_list.html', {
        'users': users,
        'role_counts': role_counts,
        'role_icons': ROLE_ICONS,
        'roles': User.ROLE_CHOICES,
        'selected_role': role,
        'selected_status': status,
        'search': search,
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
    })


@login_required
@admin_required
def user_detail(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    extra = {}
    if user_obj.role == 'parent':
        from students.models import Student
        extra['children'] = Student.objects.filter(parent=user_obj, is_active=True)
    elif user_obj.role == 'teacher':
        try:
            extra['teacher_profile'] = user_obj.teacher_profile
        except Exception:
            extra['teacher_profile'] = None
    elif user_obj.role in ('admin', 'headteacher', 'bursar'):
        try:
            extra['staff_profile'] = user_obj.staff_profile
        except Exception:
            extra['staff_profile'] = None

    return render(request, 'accounts/users/user_detail.html', {
        'user_obj': user_obj,
        'role_icon': ROLE_ICONS.get(user_obj.role, 'bi-person'),
        **extra,
    })


@login_required
@admin_required
def user_create(request):
    if request.method == 'POST':
        form = SystemUserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User "{user.username}" created successfully.')
            return redirect('accounts:user_detail', pk=user.pk)
    else:
        form = SystemUserCreateForm(initial={'is_active': True})
    return render(request, 'accounts/users/user_form.html', {
        'form': form,
        'title': 'Add System User',
    })


@login_required
@admin_required
def user_edit(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = SystemUserEditForm(request.POST, instance=user_obj, editor=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'User updated successfully.')
            return redirect('accounts:user_detail', pk=user_obj.pk)
    else:
        form = SystemUserEditForm(instance=user_obj, editor=request.user)
    return render(request, 'accounts/users/user_form.html', {
        'form': form,
        'title': f'Edit {user_obj.username}',
        'user_obj': user_obj,
    })


@login_required
@admin_required
def user_toggle_active(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if user_obj.pk == request.user.pk:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('accounts:user_detail', pk=pk)

    if request.method == 'POST':
        user_obj.is_active = not user_obj.is_active
        user_obj.save(update_fields=['is_active'])
        state = 'activated' if user_obj.is_active else 'deactivated'
        messages.success(request, f'User {user_obj.username} {state}.')
        return redirect('accounts:user_list')

    return render(request, 'accounts/users/user_toggle_active.html', {'user_obj': user_obj})


@login_required
@admin_required
def user_reset_password(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = AdminPasswordResetForm(request.POST)
        if form.is_valid():
            user_obj.set_password(form.cleaned_data['password1'])
            user_obj.save()
            messages.success(request, f'Password reset for {user_obj.username}.')
            return redirect('accounts:user_detail', pk=user_obj.pk)
    else:
        form = AdminPasswordResetForm()
    return render(request, 'accounts/users/user_reset_password.html', {
        'form': form,
        'user_obj': user_obj,
    })


@login_required
@admin_required
def user_permissions(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserPermissionsForm(request.POST, user_obj=user_obj)
        if form.is_valid():
            set_user_permissions(user_obj, form.get_permissions_dict(), granted_by=request.user)
            messages.success(request, f'Portal permissions updated for {user_obj.username}.')
            return redirect('accounts:user_detail', pk=user_obj.pk)
    else:
        form = UserPermissionsForm(user_obj=user_obj)

    modules_by_category = {}
    for code, (label, category, icon, roles) in PORTAL_MODULES.items():
        modules_by_category.setdefault(category, []).append({
            'code': code,
            'label': label,
            'icon': icon,
            'field': form[f'perm_{code}'],
            'role_default': default_access_for_role(user_obj.role, code),
            'role_list': roles,
        })

    category_sections = [
        {'key': key, 'label': CATEGORIES[key], 'modules': modules_by_category.get(key, [])}
        for key in CATEGORIES
        if modules_by_category.get(key)
    ]

    return render(request, 'accounts/users/user_permissions.html', {
        'user_obj': user_obj,
        'form': form,
        'category_sections': category_sections,
        'current_access': get_user_access_map(user_obj),
    })