from django.db import models
from django.conf import settings

class Notification(models.Model):
    TYPE_CHOICES = (
        ('message', 'Internal Message'),
        ('announcement', 'Announcement'),
        ('sms', 'SMS Alert'),
        ('email', 'Email'),
        ('fee', 'Fee Notice'),
        ('exam', 'Exam Result'),
        ('general', 'General'),
    )
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_notifications')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_notifications')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='message')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def icon_class(self):
        icons = {
            'message': 'bi-chat-dots-fill',
            'announcement': 'bi-megaphone-fill',
            'sms': 'bi-phone-fill',
            'email': 'bi-envelope-fill',
            'fee': 'bi-wallet2',
            'exam': 'bi-clipboard-check-fill',
            'general': 'bi-bell-fill',
        }
        return icons.get(self.notification_type, 'bi-bell-fill')

    @property
    def priority_icon(self):
        icons = {
            'urgent': 'bi-exclamation-octagon-fill',
            'high': 'bi-exclamation-triangle-fill',
            'medium': 'bi-info-circle-fill',
            'low': 'bi-dash-circle',
        }
        return icons.get(self.priority, 'bi-info-circle-fill')

class SMSLog(models.Model):
    recipient_number = models.CharField(max_length=15)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending')
    related_notification = models.ForeignKey(Notification, on_delete=models.SET_NULL, null=True, blank=True)