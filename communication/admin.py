from django.contrib import admin
from .models import Notification, SMSLog

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'sender', 'recipient', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('title', 'message', 'sender__username', 'recipient__username')
    readonly_fields = ('created_at',)

@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ('recipient_number', 'message_preview', 'sent_at', 'status')
    list_filter = ('status', 'sent_at')
    search_fields = ('recipient_number', 'message')
    readonly_fields = ('sent_at',)

    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message (preview)'