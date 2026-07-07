from django.views.generic import ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from .models import TimetableEntry, LessonNote, StudentResult, TimeSlot
from .forms import LessonNoteForm
from students.models import Student
from core.models import ClassRoom, Term
from teachers.models import Teacher


def can_manage_lesson_notes(user):
    return user.is_authenticated and user.role in ['admin', 'headteacher', 'teacher']

class TimetableView(LoginRequiredMixin, ListView):
    model = TimetableEntry
    template_name = 'academics/timetable.html'
    context_object_name = 'entries'

    def get_queryset(self):
        user = self.request.user
        if user.role == 'teacher':
            return TimetableEntry.objects.filter(teacher__user=user)
        elif user.role == 'student':
            return TimetableEntry.objects.filter(class_room=user.student_profile.current_class)
        return TimetableEntry.objects.all()


class LessonNotesView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = LessonNote
    template_name = 'academics/lesson_notes.html'
    context_object_name = 'notes'

    def test_func(self):
        return can_manage_lesson_notes(self.request.user)

    def get_queryset(self):
        user = self.request.user
        qs = LessonNote.objects.select_related('teacher', 'subject', 'class_room')
        if user.role == 'teacher':
            return qs.filter(teacher__user=user).order_by('-date')
        if user.role in ['admin', 'headteacher']:
            return qs.order_by('-date')
        return LessonNote.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['is_staff_view'] = user.role in ['admin', 'headteacher']
        return context


class CreateLessonNoteView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = LessonNote
    form_class = LessonNoteForm
    template_name = 'academics/lesson_note_form.html'
    success_url = reverse_lazy('academics:lesson_notes')

    def test_func(self):
        user = self.request.user
        if user.role in ['admin', 'headteacher']:
            return True
        if user.role == 'teacher':
            return Teacher.objects.filter(user=user).exists()
        return False

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['is_staff_view'] = user.role in ['admin', 'headteacher']
        return context

    def form_valid(self, form):
        user = self.request.user
        if user.role == 'teacher':
            form.instance.teacher = user.teacher_profile
        messages.success(self.request, "Lesson note created successfully.")
        return super().form_valid(form)


class ClassResultsView(LoginRequiredMixin, ListView):
    template_name = 'academics/class_results.html'
    context_object_name = 'results'

    def get_queryset(self):
        user = self.request.user
        if user.role == 'teacher':
            # Results for classes the teacher teaches
            teacher_subjects = user.teacher_profile.subjects_taught.all()
            return StudentResult.objects.filter(
                subject__in=teacher_subjects
            ).select_related('student', 'subject', 'term').order_by('-term__name')
        return StudentResult.objects.none()


def check_timetable_conflict(class_room, time_slot, term, teacher, exclude_pk=None):
    """Check for conflicts: same class+slot+term or same teacher+slot+term."""
    query = TimetableEntry.objects.filter(
        Q(class_room=class_room, time_slot=time_slot, term=term) |
        Q(teacher=teacher, time_slot=time_slot, term=term)
    )
    if exclude_pk:
        query = query.exclude(pk=exclude_pk)
    return query.exists()


class TimetableGridView(LoginRequiredMixin, ListView):
    """Visual timetable grid per class or for teacher."""
    model = TimetableEntry
    template_name = 'academics/timetable_grid.html'
    context_object_name = 'entries'

    def get_queryset(self):
        user = self.request.user
        if user.role == 'teacher':
            return TimetableEntry.objects.filter(teacher__user=user)
        class_id = self.request.GET.get('class')
        if class_id:
            return TimetableEntry.objects.filter(class_room_id=class_id)
        return TimetableEntry.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        days = ['MON', 'TUE', 'WED', 'THU', 'FRI']
        time_slots = TimeSlot.objects.all().order_by('start_time')
        # Prepare rows for easy template access
        rows = []
        for ts in time_slots:
            row = {'time_slot': ts, 'entries': {}}
            for day in days:
                row['entries'][day] = None
            rows.append(row)
        for entry in self.get_queryset():
            for row in rows:
                if row['time_slot'] == entry.time_slot:
                    row['entries'][entry.time_slot.day] = entry
                    break
        context['rows'] = rows
        context['days'] = days
        context['time_slots'] = time_slots
        context['classes'] = ClassRoom.objects.all()
        context['selected_class'] = self.request.GET.get('class')
        return context


class TimetableCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = TimetableEntry
    fields = ['class_room', 'subject', 'teacher', 'time_slot', 'term']
    template_name = 'academics/timetable_form.html'
    success_url = reverse_lazy('academics:timetable_grid')

    def test_func(self):
        return self.request.user.role in ['admin', 'headteacher']

    def form_valid(self, form):
        entry = form.instance
        if check_timetable_conflict(entry.class_room, entry.time_slot, entry.term, entry.teacher):
            messages.error(self.request, "Conflict detected: Class or teacher already has a slot at this time.")
            return self.form_invalid(form)
        messages.success(self.request, "Timetable entry created.")
        return super().form_valid(form)


class TimetableUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = TimetableEntry
    fields = ['class_room', 'subject', 'teacher', 'time_slot', 'term']
    template_name = 'academics/timetable_form.html'
    success_url = reverse_lazy('academics:timetable_grid')

    def test_func(self):
        return self.request.user.role in ['admin', 'headteacher']

    def form_valid(self, form):
        entry = form.instance
        if check_timetable_conflict(entry.class_room, entry.time_slot, entry.term, entry.teacher, exclude_pk=entry.pk):
            messages.error(self.request, "Conflict detected: Class or teacher already has a slot at this time.")
            return self.form_invalid(form)
        messages.success(self.request, "Timetable entry updated.")
        return super().form_valid(form)