from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from accounts.decorators import portal_module_required
from accounts.models import User
from accounts.permission_utils import user_can_access
from .models import Notification, SMSLog
from .utils import send_sms


def _notify_users(users, sender, title, message, notification_type='general', priority='medium'):
    """Create in-app notifications for multiple users."""
    for user in users:
        Notification.objects.create(
            sender=sender,
            recipient=user,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
        )


@login_required
@portal_module_required('communication')
@user_passes_test(lambda u: u.role in ['admin', 'headteacher'])
def send_bulk_sms(request):
    if request.method == 'POST':
        recipient_role = request.POST.get('role')
        message = request.POST.get('message')
        title = request.POST.get('subject', 'School SMS Alert')
        users = User.objects.filter(role=recipient_role, is_active=True)
        count = 0
        for user in users:
            if user.phone:
                send_sms(user.phone, message)
                SMSLog.objects.create(recipient_number=user.phone, message=message, status='sent')
                count += 1
            Notification.objects.create(
                sender=request.user,
                recipient=user,
                title=title,
                message=message,
                notification_type='sms',
                priority='high',
            )
        messages.success(request, f'Bulk SMS sent to {count} recipients.')
        return redirect('communication:bulk_communication')
    roles = User.ROLE_CHOICES if hasattr(User, 'ROLE_CHOICES') else [('parent', 'Parent'), ('teacher', 'Teacher')]
    return render(request, 'communication/send_sms.html', {'roles': roles})


@login_required
@portal_module_required('communication')
@user_passes_test(lambda u: u.role in ['admin', 'headteacher'])
def send_bulk_communication(request):
    """Bulk SMS + Email to parents, teachers, or other roles."""
    if request.method == 'POST':
        role = request.POST.get('role')
        message = request.POST.get('message')
        subject = request.POST.get('subject') or f'{request.user.get_full_name()} — School Notice'
        users = User.objects.filter(role=role, is_active=True)
        sms_count = email_count = 0
        for u in users:
            if u.phone:
                send_sms(u.phone, message)
                SMSLog.objects.create(recipient_number=u.phone, message=message, status='sent')
                sms_count += 1
                Notification.objects.create(
                    sender=request.user, recipient=u, title=subject, message=message,
                    notification_type='sms', priority='high',
                )
            if u.email:
                send_mail(
                    subject, message,
                    settings.DEFAULT_FROM_EMAIL or 'no-reply@happychild.ug',
                    [u.email], fail_silently=True,
                )
                email_count += 1
                Notification.objects.create(
                    sender=request.user, recipient=u, title=subject, message=message,
                    notification_type='email', priority='medium',
                )
        messages.success(request, f'Sent: {sms_count} SMS, {email_count} emails. In-app notifications created.')
        return redirect('communication:bulk_communication')
    return render(request, 'communication/bulk.html')


@login_required
@portal_module_required('communication')
def message_inbox(request):
    """Notifications inbox for staff, teachers, and parents."""
    received = Notification.objects.filter(recipient=request.user).select_related('sender').order_by('-created_at')
    sent = Notification.objects.filter(sender=request.user).select_related('recipient').order_by('-created_at')[:15]
    unread_count = received.filter(is_read=False).count()
    return render(request, 'communication/inbox.html', {
        'received': received,
        'sent': sent,
        'unread_count': unread_count,
    })


@login_required
@portal_module_required('communication')
def notification_detail(request, pk):
    notification = get_object_or_404(
        Notification.objects.select_related('sender'),
        pk=pk,
        recipient=request.user,
    )
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])
    return render(request, 'communication/notification_detail.html', {'notification': notification})


@login_required
@portal_module_required('communication')
def mark_all_read(request):
    if request.method == 'POST':
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        messages.success(request, 'All notifications marked as read.')
    return redirect('communication:inbox')


@login_required
@portal_module_required('communication')
def send_internal_message(request):
    can_send_to_parents = request.user.role in ['admin', 'headteacher']
    if request.method == 'POST':
        recipient_id = request.POST.get('recipient')
        title = request.POST.get('title')
        message = request.POST.get('message')
        priority = request.POST.get('priority', 'medium')
        try:
            recipient = User.objects.get(id=recipient_id, is_active=True)
            if recipient.role == 'parent' and not can_send_to_parents:
                messages.error(request, 'You cannot message parents.')
                return redirect('communication:send_message')
            Notification.objects.create(
                sender=request.user,
                recipient=recipient,
                title=title,
                message=message,
                notification_type='message',
                priority=priority,
            )
            messages.success(request, 'Message sent successfully.')
        except User.DoesNotExist:
            messages.error(request, 'Recipient not found.')
        return redirect('communication:inbox')

    if can_send_to_parents:
        recipients = User.objects.filter(
            role__in=['admin', 'headteacher', 'teacher', 'bursar', 'parent'],
            is_active=True,
        ).order_by('role', 'first_name')
    else:
        recipients = User.objects.filter(
            role__in=['admin', 'headteacher', 'teacher', 'bursar'],
            is_active=True,
        ).order_by('role', 'first_name')
    return render(request, 'communication/send_message.html', {
        'recipients': recipients,
        'can_send_to_parents': can_send_to_parents,
    })