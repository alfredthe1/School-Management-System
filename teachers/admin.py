from django.contrib import admin
from .models import Teacher

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'first_name', 'last_name', 'qualification', 'is_active')
    list_filter = ('is_active', 'gender')
    search_fields = ('first_name', 'last_name', 'employee_id', 'qualification')
    readonly_fields = ('employee_id', 'date_joined')
    filter_horizontal = ('subjects_taught',)