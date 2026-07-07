from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.db.models import Q, Avg
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from .models import Student
from .forms import StudentForm, StudentResultForm
from core.models import ClassRoom
from accounts.permission_utils import user_can_access
from core.helpers import get_teacher_class_ids, teacher_teaches_student, get_teacher_subject_ids
from teachers.models import Teacher
from examinations.models import Exam, ExamResult
from academics.models import StudentResult
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io


class StudentListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Student
    template_name = 'students/student_list.html'
    context_object_name = 'students'

    def test_func(self):
        user = self.request.user
        if not user_can_access(user, 'students'):
            return False
        return user.role in ['admin', 'headteacher', 'teacher', 'bursar']

    def get_queryset(self):
        queryset = Student.objects.select_related('current_class', 'parent').order_by(
            'last_name', 'first_name'
        )
        user = self.request.user
        if user.role == 'teacher':
            class_ids = get_teacher_class_ids(user)
            queryset = queryset.filter(current_class_id__in=class_ids, is_active=True)
        elif user.role == 'bursar':
            queryset = queryset.filter(is_active=True)
        class_filter = self.request.GET.get('class')
        if class_filter:
            queryset = queryset.filter(current_class_id=class_filter)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.role == 'teacher':
            class_ids = get_teacher_class_ids(user)
            context['class_list'] = ClassRoom.objects.filter(id__in=class_ids).order_by('name')
        else:
            context['class_list'] = ClassRoom.objects.all().order_by('name')
        context['is_teacher_view'] = user.role == 'teacher'
        context['is_bursar_view'] = user.role == 'bursar'
        context['can_edit_marks'] = user.role in ['admin', 'headteacher', 'teacher']
        context['can_manage_fees'] = user.role in ['admin', 'headteacher', 'bursar']
        for student in context['students']:
            student.total_paid = student.get_total_fees_paid()
            student.balance = student.get_fees_balance()
        return context


class StudentDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Student
    template_name = 'students/student_detail.html'

    def test_func(self):
        user = self.request.user
        if not user_can_access(user, 'students'):
            return False
        if user.role in ['admin', 'headteacher', 'bursar']:
            return True
        if user.role == 'teacher':
            student = get_object_or_404(Student, pk=self.kwargs.get('pk'))
            return teacher_teaches_student(user, student)
        return False


class StudentCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = 'students/student_form.html'
    success_url = reverse_lazy('students:list')

    def test_func(self):
        return self.request.user.role in ['admin', 'headteacher']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Student'
        return context

    def form_valid(self, form):
        messages.success(self.request, f"Student {form.instance.get_full_name()} added successfully with ID: {form.instance.student_id}")
        return super().form_valid(form)


class StudentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = 'students/student_form.html'
    success_url = reverse_lazy('students:list')

    def test_func(self):
        return self.request.user.role in ['admin', 'headteacher']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Student: {self.object.get_full_name()}'
        return context

    def form_valid(self, form):
        messages.success(self.request, f"Student {form.instance.get_full_name()} updated successfully.")
        return super().form_valid(form)


class StudentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Student
    template_name = 'students/student_confirm_delete.html'
    success_url = reverse_lazy('students:list')

    def test_func(self):
        return self.request.user.role in ['admin', 'headteacher']

    def delete(self, request, *args, **kwargs):
        student = self.get_object()
        messages.success(request, f"Student {student.get_full_name()} deleted successfully.")
        return super().delete(request, *args, **kwargs)


class StudentPDFView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.role in ['admin', 'headteacher']

    def get(self, request, *args, **kwargs):
        # Build queryset with filters (same as list view)
        queryset = Student.objects.all().order_by('last_name', 'first_name')
        search = request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(student_id__icontains=search)
            )
        class_filter = request.GET.get('class')
        if class_filter:
            queryset = queryset.filter(current_class_id=class_filter)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)

        elements = []
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=12
        )
        subtitle_style = ParagraphStyle(
            'SubtitleStyle',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            textColor=colors.grey,
            spaceAfter=20
        )

        from core.context_processors import school_info
        info = school_info(request)
        school_name = info.get('school_name', 'Happy Child School')
        motto = info.get('school_motto', 'Always an achiever')

        elements.append(Paragraph(f"<b>{school_name}</b>", title_style))
        elements.append(Paragraph(f"{motto}", subtitle_style))
        elements.append(Paragraph("Student List", styles['Heading2']))
        elements.append(Spacer(1, 0.2 * inch))

        # Table data
        data = []
        headers = ['ID', 'Name', 'Class', 'Parent', 'Fees Paid', 'Balance', 'Status']
        data.append(headers)

        for student in queryset:
            # Parent name – fallback to username if full name is empty
            parent_name = 'None'
            if student.parent:
                parent_name = student.parent.get_full_name()
                if not parent_name:
                    parent_name = student.parent.username

            row = [
                student.student_id,
                student.get_full_name(),
                str(student.current_class) if student.current_class else 'N/A',
                parent_name,
                f"UGX {student.get_total_fees_paid():,.0f}",
                f"UGX {student.get_fees_balance():,.0f}",
                'Active' if student.is_active else 'Inactive'
            ]
            data.append(row)

        table = Table(data, repeatRows=1, colWidths=[0.8*inch, 1.5*inch, 1.2*inch, 1.5*inch, 1.0*inch, 1.0*inch, 0.8*inch])
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C7BB6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (4, 1), (5, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
        # Alternate row colors
        for i in range(1, len(data)):
            if i % 2 == 0:
                style.add('BACKGROUND', (0, i), (-1, i), colors.whitesmoke)
        table.setStyle(style)
        elements.append(table)

        # Build PDF
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="student_list.pdf"'
        return response


def can_view_student_results(user, student):
    if user.role in ['admin', 'headteacher', 'bursar']:
        return True
    if user.role == 'teacher':
        return teacher_teaches_student(user, student)
    return False


def can_edit_student_results(user, student):
    if user.role in ['admin', 'headteacher']:
        return True
    if user.role == 'teacher':
        if not student.current_class_id:
            return False
        return bool(get_teacher_subject_ids(user, class_room=student.current_class))
    return False


def _get_student_exams(student, user):
    if not student.current_class:
        return Exam.objects.none()
    exams = Exam.objects.filter(class_room=student.current_class).select_related(
        'subject', 'term'
    ).order_by('-start_date')
    if user.role == 'teacher':
        subject_ids = get_teacher_subject_ids(user, class_room=student.current_class)
        exams = exams.filter(subject_id__in=subject_ids)
    return exams


def _get_exam_results_map(student, exams):
    results = ExamResult.objects.filter(student=student, exam__in=exams)
    return {r.exam_id: r for r in results}


def _get_continuous_results(student, user):
    qs = StudentResult.objects.filter(student=student).select_related('subject', 'term')
    if user.role == 'teacher':
        subject_ids = get_teacher_subject_ids(user, class_room=student.current_class)
        qs = qs.filter(subject_id__in=subject_ids)
    return qs.order_by('-term__name', 'subject__name')


@login_required
def student_results(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if not can_view_student_results(request.user, student):
        return HttpResponseForbidden('You do not have permission to view these results.')

    exams = _get_student_exams(student, request.user)
    results_map = _get_exam_results_map(student, exams)
    exam_rows = []
    for exam in exams:
        result = results_map.get(exam.id)
        exam_rows.append({'exam': exam, 'result': result})

    continuous_results = _get_continuous_results(student, request.user)
    exam_avg = ExamResult.objects.filter(
        student=student, exam__in=exams
    ).aggregate(avg=Avg('marks_obtained'))['avg']

    return render(request, 'students/student_results.html', {
        'student': student,
        'exam_rows': exam_rows,
        'continuous_results': continuous_results,
        'exam_avg': round(exam_avg, 1) if exam_avg else None,
        'can_edit': can_edit_student_results(request.user, student),
    })


@login_required
def student_results_edit(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if not can_edit_student_results(request.user, student):
        return HttpResponseForbidden('You do not have permission to edit these results.')

    exams = _get_student_exams(student, request.user)
    results_map = _get_exam_results_map(student, exams)
    continuous_results = _get_continuous_results(student, request.user)
    is_staff = request.user.role in ['admin', 'headteacher']

    if request.method == 'POST':
        saved_exam = 0
        for exam in exams:
            marks = request.POST.get(f'exam_{exam.id}')
            remarks = request.POST.get(f'remarks_{exam.id}', '')
            if marks is not None and marks != '':
                result, _ = ExamResult.objects.get_or_create(exam=exam, student=student)
                result.marks_obtained = marks
                result.remarks = remarks
                result.save()
                saved_exam += 1

        for ca in continuous_results:
            test_key = f'ca_test_{ca.id}'
            exam_key = f'ca_exam_{ca.id}'
            grade_key = f'ca_grade_{ca.id}'
            if test_key in request.POST or exam_key in request.POST:
                ca.test_score = request.POST.get(test_key) or 0
                ca.exam_score = request.POST.get(exam_key) or 0
                ca.grade = request.POST.get(grade_key, '')
                ca.save()

        if is_staff and request.POST.get('add_ca') == '1':
            form = StudentResultForm(request.POST, student=student, user=request.user)
            if form.is_valid():
                ca = form.save(commit=False)
                ca.student = student
                ca.save()
                messages.success(request, 'Continuous assessment record added.')
            else:
                messages.error(request, 'Could not add continuous assessment. Check the form.')
                return render(request, 'students/student_results_edit.html', {
                    'student': student,
                    'exam_rows': [{'exam': e, 'result': results_map.get(e.id)} for e in exams],
                    'continuous_results': continuous_results,
                    'ca_form': form,
                    'is_staff': is_staff,
                })

        messages.success(request, f'Results saved ({saved_exam} exam mark(s) updated).')
        return redirect('students:results', pk=student.pk)

    ca_form = StudentResultForm(student=student, user=request.user)
    exam_rows = [{'exam': exam, 'result': results_map.get(exam.id)} for exam in exams]

    return render(request, 'students/student_results_edit.html', {
        'student': student,
        'exam_rows': exam_rows,
        'continuous_results': continuous_results,
        'ca_form': ca_form,
        'is_staff': is_staff,
    })