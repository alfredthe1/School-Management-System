from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.db.models import Q
from django.contrib import messages
from django.http import HttpResponse
from accounts.permission_utils import user_can_access
from .models import Teacher
from .forms import TeacherForm
from core.models import Subject
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
import io


class TeacherListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Teacher
    template_name = 'teachers/teacher_list.html'
    context_object_name = 'teachers'
    def test_func(self):
        user = self.request.user
        return user_can_access(user, 'teachers') and user.role in ['admin', 'headteacher']

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(employee_id__icontains=search) |
                Q(qualification__icontains=search)
            )
        subject_filter = self.request.GET.get('subject')
        if subject_filter:
            queryset = queryset.filter(subjects_taught__id=subject_filter)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subject_list'] = Subject.objects.all().order_by('name')
        return context


class TeacherDetailView(LoginRequiredMixin, DetailView):
    model = Teacher
    template_name = 'teachers/teacher_detail.html'


class TeacherCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Teacher
    form_class = TeacherForm
    template_name = 'teachers/teacher_form.html'
    success_url = reverse_lazy('teachers:list')

    def test_func(self):
        user = self.request.user
        return user_can_access(user, 'teachers') and user.role in ['admin', 'headteacher']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Teacher'
        return context

    def form_valid(self, form):
        messages.success(self.request, f"Teacher {form.instance.get_full_name()} added successfully with ID: {form.instance.employee_id}")
        return super().form_valid(form)


class TeacherUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Teacher
    form_class = TeacherForm
    template_name = 'teachers/teacher_form.html'
    success_url = reverse_lazy('teachers:list')

    def test_func(self):
        user = self.request.user
        return user_can_access(user, 'teachers') and user.role in ['admin', 'headteacher']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Teacher: {self.object.get_full_name()}'
        # Pre-populate username field with user's username
        if self.object.user:
            context['form'].fields['username'].initial = self.object.user.username
        return context

    def form_valid(self, form):
        messages.success(self.request, f"Teacher {form.instance.get_full_name()} updated successfully.")
        return super().form_valid(form)


class TeacherDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Teacher
    template_name = 'teachers/teacher_confirm_delete.html'
    success_url = reverse_lazy('teachers:list')

    def test_func(self):
        user = self.request.user
        return user_can_access(user, 'teachers') and user.role in ['admin', 'headteacher']

    def delete(self, request, *args, **kwargs):
        teacher = self.get_object()
        # Optionally delete the user account as well
        user = teacher.user
        teacher.delete()
        if user:
            user.delete()
        messages.success(request, f"Teacher {teacher.get_full_name()} deleted successfully.")
        return super().delete(request, *args, **kwargs)


class TeacherPDFView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        user = self.request.user
        return user_can_access(user, 'teachers') and user.role in ['admin', 'headteacher']

    def get(self, request, *args, **kwargs):
        queryset = Teacher.objects.all().order_by('last_name', 'first_name')
        search = request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(employee_id__icontains=search)
            )
        subject_filter = request.GET.get('subject')
        if subject_filter:
            queryset = queryset.filter(subjects_taught__id=subject_filter)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)

        elements = []
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER, spaceAfter=10)
        subtitle_style = ParagraphStyle('SubtitleStyle', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, textColor=colors.grey, spaceAfter=20)

        from core.context_processors import school_info
        info = school_info(request)
        school_name = info.get('school_name', 'Happy Child School')
        elements.append(Paragraph(f"<b>{school_name}</b>", title_style))
        elements.append(Paragraph("Teacher List", subtitle_style))
        elements.append(Spacer(1, 0.2 * inch))

        data = [['ID', 'Name', 'Qualification', 'Subjects', 'Status']]
        for t in queryset:
            subjects = ', '.join([s.name for s in t.subjects_taught.all()]) or 'None'
            data.append([
                t.employee_id,
                t.get_full_name(),
                t.qualification or 'N/A',
                subjects,
                'Active' if t.is_active else 'Inactive'
            ])

        table = Table(data, repeatRows=1, colWidths=[1.0*inch, 1.8*inch, 1.8*inch, 2.5*inch, 0.8*inch])
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C7BB6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ])
        for i in range(1, len(data)):
            if i % 2 == 0:
                style.add('BACKGROUND', (0, i), (-1, i), colors.whitesmoke)
        table.setStyle(style)
        elements.append(table)

        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="teachers_list.pdf"'
        return response