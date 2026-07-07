from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from .models import User, UserPortalPermission


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'role', 'phone', 'address', 'profile_pic')


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    list_display = ('username', 'email', 'role', 'phone', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'phone')
    ordering = ('username',)

    fieldsets = UserAdmin.fieldsets + (
        ('School Info', {'fields': ('role', 'phone', 'address', 'profile_pic')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'phone', 'address', 'profile_pic'),
        }),
    )


@admin.register(UserPortalPermission)
class UserPortalPermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'module', 'is_allowed', 'granted_by', 'updated_at')
    list_filter = ('module', 'is_allowed', 'user__role')
    search_fields = ('user__username', 'module')
    raw_id_fields = ('user', 'granted_by')