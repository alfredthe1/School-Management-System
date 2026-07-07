from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from accounts.models import User
from communication.models import Notification
from .models import Announcement

PRIORITY_MAP = {
    'urgent': 'urgent',
    'high': 'high',
    'medium': 'medium',
    'low': 'low',
}


def _users_for_roles(target_roles):
    if not target_roles:
        return User.objects.filter(is_active=True)
    roles = [r.strip() for r in target_roles.split(',') if r.strip()]
    return User.objects.filter(role__in=roles, is_active=True)


@login_required
def announcement_list(request):
    announcements = Announcement.objects.filter(is_active=True).select_related('author').order_by('-created_at')
    user_role = request.user.role
    filtered = []
    for a in announcements:
        if not a.target_roles or user_role in [r.strip() for r in a.target_roles.split(',')]:
            filtered.append(a)
    return render(request, 'announcements/list.html', {'announcements': filtered})


@login_required
@user_passes_test(lambda u: u.role in ['admin', 'headteacher'])
def create_announcement(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        priority = request.POST.get('priority', 'medium')
        target_roles = request.POST.get('target_roles', 'parent,teacher')
        if title and content:
            announcement = Announcement.objects.create(
                title=title,
                content=content,
                author=request.user,
                priority=priority,
                target_roles=target_roles,
            )
            recipients = _users_for_roles(target_roles).exclude(pk=request.user.pk)
            for user in recipients:
                Notification.objects.create(
                    sender=request.user,
                    recipient=user,
                    title=f'Announcement: {title}',
                    message=content,
                    notification_type='announcement',
                    priority=PRIORITY_MAP.get(priority, 'medium'),
                )
            messages.success(request, f'Announcement published to {recipients.count()} users.')
            return redirect('announcements:list')
    return render(request, 'announcements/create.html')