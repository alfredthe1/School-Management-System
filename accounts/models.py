from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('headteacher', 'Head Teacher'),
        ('teacher', 'Teacher'),
        ('bursar', 'Bursar'),
        ('parent', 'Parent'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='parent')
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def can_access(self, module_code):
        from accounts.permission_utils import user_can_access
        return user_can_access(self, module_code)


class UserPortalPermission(models.Model):
    """Per-user override for portal module visibility (admin-configurable)."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='portal_permission_overrides',
    )
    module = models.CharField(max_length=50)
    is_allowed = models.BooleanField(default=True)
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='permissions_granted',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'module']
        verbose_name = 'portal permission'
        verbose_name_plural = 'portal permissions'

    def __str__(self):
        state = 'allow' if self.is_allowed else 'deny'
        return f'{self.user.username} — {self.module} ({state})'