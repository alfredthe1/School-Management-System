from django.contrib import admin
from .models import TimeSlot, TimetableEntry, LessonNote, StudentResult

@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('day', 'start_time', 'end_time')
    list_filter = ('day',)
    ordering = ('day', 'start_time')

@admin.register(TimetableEntry)
class TimetableEntryAdmin(admin.ModelAdmin):
    list_display = ('class_room', 'subject', 'teacher', 'time_slot', 'term')
    list_filter = ('class_room', 'term', 'time_slot__day')
    search_fields = ('class_room__name', 'subject__name', 'teacher__user__username')

@admin.register(LessonNote)
class LessonNoteAdmin(admin.ModelAdmin):
    list_display = ('subject', 'teacher', 'class_room', 'date', 'topic')
    list_filter = ('subject', 'teacher', 'class_room', 'date')
    search_fields = ('topic', 'content')

@admin.register(StudentResult)
class StudentResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'term', 'test_score', 'exam_score', 'total', 'grade')
    list_filter = ('subject', 'term', 'grade')
    search_fields = ('student__user__username', 'student__student_id')
    readonly_fields = ('total',)