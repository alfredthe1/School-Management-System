from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from django.db.models import Avg, Sum
from django import forms
import io

from students.models import Student
from examinations.models import ExamResult
from fees.models import Payment, FeeStructure
from core.models import AcademicYear, ClassRoom, Term
from accounts.models import User

def report_manager_check(user):
    return user.role in ['admin', 'headteacher', 'bursar']

@login_required
@user_passes_test(report_manager_check)
def generate_class_report_excel(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Student Report"
    ws.append(['Student ID', 'Name', 'Class', 'Average Score'])
    students = Student.objects.all()
    for student in students:
        avg = ExamResult.objects.filter(student=student).aggregate(avg=Avg('marks_obtained'))['avg'] or 0
        ws.append([student.student_id, student.get_full_name() if hasattr(student, 'get_full_name') else f"{student.first_name} {student.last_name}", str(student.current_class), round(avg, 1) if avg else 'N/A'])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=student_report.xlsx'
    wb.save(response)
    return response

@login_required
def student_report_card(request, student_id):
    """Generate professional report card PDF."""
    from core.context_processors import school_info as get_school_info
    from .report_card_pdf import build_report_card_pdf

    student = get_object_or_404(Student, id=student_id)
    user = request.user
    staff_roles = ['admin', 'headteacher', 'teacher', 'bursar']

    if user.role == 'parent':
        return HttpResponse(
            'Report card printing is available through the school office. '
            'You can view results on your child\'s progress page.',
            status=403,
        )
    elif user.role in staff_roles:
        if user.role == 'teacher':
            from core.helpers import teacher_teaches_student
            if not teacher_teaches_student(user, student):
                return HttpResponse('Access denied', status=403)
        parent_view = False
    else:
        return HttpResponse('Access denied', status=403)

    info = get_school_info(request)
    pdf = build_report_card_pdf(student, school_info=info, parent_view=parent_view)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'inline; filename="report_card_{student.student_id}.pdf"'
    )
    return response

@login_required
def fee_balance_statement(request, student_id=None):
    """Fee balance statement PDF."""
    if student_id:
        student = get_object_or_404(Student, id=student_id)
        payments = Payment.objects.filter(student=student)
    else:
        # For bursar, list or something
        return HttpResponse("Specify student")

    # Similar PDF generation for balance
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph(f"Fee Balance Statement for {student}", styles['Heading2']))
    # ... add table of payments ...
    data = [['Date', 'Amount', 'Method', 'Receipt']]
    for p in payments:
        data.append([str(p.date_paid), p.amount_paid, p.payment_method, p.receipt_number])
    t = Table(data)
    t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4AA3DF')), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
    elements.append(t)
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename=balance_{student.student_id}.pdf'
    return resp

class CustomReportForm(forms.Form):
    REPORT_TYPES = [
        ('students', 'Student List'),
        ('fees', 'Fee Collection'),
        ('exams', 'Exam Results Summary'),
    ]
    report_type = forms.ChoiceField(choices=REPORT_TYPES)
    class_room = forms.ModelChoiceField(queryset=ClassRoom.objects.all(), required=False)
    term = forms.ModelChoiceField(queryset=Term.objects.all(), required=False)

@login_required
@user_passes_test(report_manager_check)
def custom_report_builder(request):
    form = CustomReportForm(request.GET or None)
    report_data = None
    if form.is_valid():
        rtype = form.cleaned_data['report_type']
        cls = form.cleaned_data.get('class_room')
        term = form.cleaned_data.get('term')
        if rtype == 'students':
            qs = Student.objects.all()
            if cls: qs = qs.filter(current_class=cls)
            report_data = list(qs.values('student_id', 'first_name', 'last_name', 'current_class__name'))
        elif rtype == 'fees':
            qs = Payment.objects.all()
            if cls: qs = qs.filter(student__current_class=cls)
            report_data = [{'total': qs.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0}]
        # etc for exams
    return render(request, 'reports/custom_builder.html', {'form': form, 'report_data': report_data})