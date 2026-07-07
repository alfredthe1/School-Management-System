from django.contrib import admin
from .models import Student

class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'first_name', 'last_name', 'current_class', 'parent', 'is_active')
    list_filter = ('current_class', 'gender', 'is_active')
    search_fields = ('first_name', 'last_name', 'student_id')
    readonly_fields = ('enrollment_date',)

admin.site.register(Student, StudentAdmin)