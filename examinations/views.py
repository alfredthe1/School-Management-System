from decimal import Decimal, InvalidOperation

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Avg, Count
from .models import Exam, ExamResult, GradeScale
from .forms import ExamForm, GradeScaleForm
from .teacher_utils import (
    exam_marking_stats,
    get_teacher_subjects,
    teacher_can_edit_exam,
    teacher_subject_assignments,
    teacher_teaches_subject,
)
from students.models import Student
from core.models import Subject, Term


def is_staff_manager(user):
    return user.is_authenticated and user.role in ['admin', 'headteacher']


# ---------- TEACHER VIEWS ----------
@login_required
def teacher_marks_hub(request):
    """Teacher home for marks: subjects taught, exams, and quick entry."""
    if request.user.role != 'teacher':
        messages.error(request, 'This page is for teachers only.')
        return redirect('examinations:exam_list' if is_staff_manager(request.user) else 'core:dashboard')

    assignments = teacher_subject_assignments(request.user)
    subject_ids = get_teacher_subjects(request.user).values_list('id', flat=True)
    exams = Exam.objects.filter(subject_id__in=subject_ids).select_related(
        'subject', 'class_room', 'term'
    ).order_by('-start_date')

    term_id = request.GET.get('term')
    class_id = request.GET.get('class')
    subject_id = request.GET.get('subject')
    if term_id:
        exams = exams.filter(term_id=term_id)
    if class_id:
        exams = exams.filter(class_room_id=class_id)
    if subject_id:
        exams = exams.filter(subject_id=subject_id)

    exam_rows = []
    for exam in exams:
        stats = exam_marking_stats(exam)
        exam_rows.append({'exam': exam, **stats})

    classes = {a['class_room'].id: a['class_room'] for a in assignments}.values()
    subjects = get_teacher_subjects(request.user)

    return render(request, 'examinations/teacher_marks_hub.html', {
        'assignments': assignments,
        'exam_rows': exam_rows,
        'terms': Term.objects.select_related('academic_year').order_by('-academic_year__name'),
        'classes': sorted(classes, key=lambda c: c.name),
        'subjects': subjects,
        'selected_term': term_id or '',
        'selected_class': class_id or '',
        'selected_subject': subject_id or '',
    })


@login_required
def teacher_exam_list(request):
    if request.user.role != 'teacher':
        messages.error(request, 'This page is for teachers only.')
        return redirect('examinations:exam_list' if is_staff_manager(request.user) else 'core:dashboard')

    return redirect('examinations:teacher_marks_hub')


@login_required
def teacher_enter_marks(request, exam_id):
    exam = get_object_or_404(Exam.objects.select_related('subject', 'class_room', 'term'), id=exam_id)
    if not teacher_can_edit_exam(request.user, exam):
        messages.error(request, 'You can only enter marks for subjects you teach.')
        return redirect('examinations:teacher_marks_hub' if request.user.role == 'teacher' else 'examinations:exam_list')

    students = Student.objects.filter(
        current_class=exam.class_room, is_active=True
    ).order_by('last_name', 'first_name')
    results = {r.student_id: r for r in ExamResult.objects.filter(exam=exam)}

    if request.method == 'POST':
        saved = 0
        errors = 0
        for student in students:
            marks_raw = request.POST.get(f'marks_{student.id}')
            remarks = request.POST.get(f'remarks_{student.id}', '').strip()
            if marks_raw is None or marks_raw == '':
                continue
            try:
                marks = Decimal(marks_raw)
            except (InvalidOperation, ValueError):
                errors += 1
                continue
            if marks < 0 or marks > exam.max_marks:
                errors += 1
                continue
            result, _ = ExamResult.objects.get_or_create(exam=exam, student=student)
            result.marks_obtained = marks
            result.remarks = remarks
            result.save()
            saved += 1
        if saved:
            messages.success(
                request,
                f'Marks saved for {saved} student(s) in {exam.subject.name} ({exam.class_room}).',
            )
        if errors:
            messages.warning(request, f'{errors} mark(s) were skipped (invalid or out of range).')
        if request.user.role == 'teacher':
            return redirect('examinations:teacher_marks_hub')
        return redirect('examinations:exam_results', exam_id=exam.id)

    student_rows = []
    for student in students:
        existing = results.get(student.id)
        student_rows.append({'student': student, 'result': existing})

    return render(request, 'examinations/enter_marks.html', {
        'exam': exam,
        'student_rows': student_rows,
        'stats': exam_marking_stats(exam),
        'grade_scale': GradeScale.objects.all().order_by('-min_score'),
        'can_edit': True,
    })


@login_required
def teacher_view_results(request):
    if request.user.role == 'teacher':
        subjects = get_teacher_subjects(request.user)
        exams = Exam.objects.filter(subject__in=subjects).select_related(
            'subject', 'class_room', 'term'
        ).order_by('-start_date')
    elif is_staff_manager(request.user):
        exams = Exam.objects.select_related('subject', 'class_room', 'term').order_by('-start_date')
    else:
        messages.error(request, 'Access denied.')
        return redirect('core:dashboard')

    exam_stats = []
    for exam in exams:
        stats = ExamResult.objects.filter(exam=exam).aggregate(
            avg=Avg('marks_obtained'), count=Count('id')
        )
        exam_stats.append({
            'exam': exam,
            'avg': round(stats['avg'], 1) if stats['avg'] else None,
            'count': stats['count'],
        })

    return render(request, 'examinations/teacher_view_results.html', {'exam_stats': exam_stats})


@login_required
def teacher_result_detail(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if request.user.role == 'teacher' and not teacher_teaches_subject(request.user, exam.subject):
        messages.error(request, 'You can only view results for subjects you teach.')
        return redirect('examinations:teacher_view_results')
    if request.user.role not in ['teacher', 'admin', 'headteacher']:
        messages.error(request, 'Access denied.')
        return redirect('core:dashboard')

    results = ExamResult.objects.filter(exam=exam).select_related('student').order_by(
        '-marks_obtained'
    )
    stats = results.aggregate(avg=Avg('marks_obtained'), count=Count('id'))
    return render(request, 'examinations/teacher_result_detail.html', {
        'exam': exam,
        'results': results,
        'avg_score': round(stats['avg'], 1) if stats['avg'] else None,
        'total_students': stats['count'],
        'can_edit': teacher_can_edit_exam(request.user, exam),
        'marking_stats': exam_marking_stats(exam),
    })


@login_required
@user_passes_test(is_staff_manager)
def exam_results(request, exam_id):
    return teacher_result_detail(request, exam_id)


# ---------- ADMIN/HEADTEACHER CRUD ----------
class ExamListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Exam
    template_name = 'examinations/exam_list.html'
    context_object_name = 'exams'

    def test_func(self):
        return is_staff_manager(self.request.user)

    def get_queryset(self):
        return Exam.objects.select_related('subject', 'class_room', 'term').order_by('-start_date')


class ExamCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Exam
    form_class = ExamForm
    template_name = 'examinations/exam_form.html'
    success_url = reverse_lazy('examinations:exam_list')

    def test_func(self):
        return is_staff_manager(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Exam created successfully.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Exam'
        return context


class ExamUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Exam
    form_class = ExamForm
    template_name = 'examinations/exam_form.html'
    success_url = reverse_lazy('examinations:exam_list')

    def test_func(self):
        return is_staff_manager(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Exam updated successfully.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Exam'
        return context


class ExamDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Exam
    template_name = 'examinations/exam_confirm_delete.html'
    success_url = reverse_lazy('examinations:exam_list')

    def test_func(self):
        return is_staff_manager(self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Exam deleted successfully.')
        return super().delete(request, *args, **kwargs)


@login_required
@user_passes_test(is_staff_manager)
def grade_scale_list(request):
    scales = GradeScale.objects.all().order_by('-min_score')
    if request.method == 'POST':
        form = GradeScaleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Grade scale added.')
            return redirect('examinations:grade_scales')
    else:
        form = GradeScaleForm()
    return render(request, 'examinations/grade_scales.html', {'scales': scales, 'form': form})


@login_required
@user_passes_test(is_staff_manager)
def grade_scale_delete(request, pk):
    scale = get_object_or_404(GradeScale, pk=pk)
    if request.method == 'POST':
        scale.delete()
        messages.success(request, 'Grade scale removed.')
    return redirect('examinations:grade_scales')