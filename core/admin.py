# Register your models here.
from django.contrib import admin
from .models import AcademicYear, Term, ClassRoom, Subject, Event, SchoolPortalSettings

admin.site.register(AcademicYear)
admin.site.register(Term)
admin.site.register(ClassRoom)
admin.site.register(Subject)

# core/admin.py (after existing registrations)
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'is_upcoming')
    list_filter = ('is_upcoming', 'date')
    search_fields = ('title', 'description')


@admin.register(SchoolPortalSettings)
class SchoolPortalSettingsAdmin(admin.ModelAdmin):
    list_display = ('block_parent_results_on_fee_balance', 'updated_at')

    def has_add_permission(self, request):
        return not SchoolPortalSettings.objects.exists()