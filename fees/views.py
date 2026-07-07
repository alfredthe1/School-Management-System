from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import View
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from django.urls import reverse
from django.http import HttpResponse

from accounts.decorators import admin_required, portal_module_required
from core.models import AcademicYear, ClassRoom, SchoolPortalSettings
from core.parent_results_access import effective_access_label, parent_can_view_results
from fees.payment_config import get_payment_gateway_status
from students.models import Student
from .models import FeeStructure, Payment, Expenditure
from .forms import (
    ExpenditureForm,
    FeeStructureForm,
    ParentResultsPolicyForm,
    PaymentForm,
    RecordPaymentForm,
)

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io


# -------------------- HELPER --------------------
def fee_manager_check(user):
    from accounts.permission_utils import user_can_access
    return user.is_authenticated and user_can_access(user, 'fees')


def fee_structure_admin_check(user):
    """Only administrators may create, edit, or delete fee structures."""
    return user.is_authenticated and user.role == 'admin'


# -------------------- DASHBOARD --------------------
@login_required
@user_passes_test(fee_manager_check)
def fee_dashboard(request):
    current_year = AcademicYear.objects.filter(is_current=True).first()
    today = timezone.now().date()
    this_month = today.replace(day=1)

    total_collected = Payment.objects.aggregate(total=Sum('amount_paid'))['total'] or 0
    today_collected = Payment.objects.filter(date_paid=today).aggregate(total=Sum('amount_paid'))['total'] or 0
    month_collected = Payment.objects.filter(date_paid__gte=this_month).aggregate(total=Sum('amount_paid'))['total'] or 0
    total_expenditure = Expenditure.objects.aggregate(total=Sum('amount'))['total'] or 0
    month_expenditure = Expenditure.objects.filter(date__gte=this_month).aggregate(total=Sum('amount'))['total'] or 0

    pending_fees = 0
    if current_year:
        total_due_all = FeeStructure.objects.filter(academic_year=current_year).aggregate(total=Sum('amount'))['total'] or 0
        pending_fees = total_due_all - total_collected

    context = {
        'total_collected': total_collected,
        'today_collected': today_collected,
        'month_collected': month_collected,
        'total_expenditure': total_expenditure,
        'month_expenditure': month_expenditure,
        'pending_fees': max(pending_fees, 0),
        'current_year': current_year,
    }
    return render(request, 'fees/dashboard.html', context)


# -------------------- FEE STRUCTURES --------------------
@login_required
@user_passes_test(fee_manager_check)
def fee_structure_list(request):
    structures = FeeStructure.objects.select_related('academic_year', 'class_room').all().order_by('-academic_year__name', 'class_room__name')
    return render(request, 'fees/fee_structure_list.html', {'structures': structures})

@login_required
@user_passes_test(fee_structure_admin_check)
def fee_structure_add(request):
    if request.method == 'POST':
        form = FeeStructureForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Fee structure added successfully.")
            return redirect('fees:fee_structure_list')
    else:
        form = FeeStructureForm()
    return render(request, 'fees/fee_structure_form.html', {'form': form, 'title': 'Add Fee Structure'})

@login_required
@user_passes_test(fee_structure_admin_check)
def fee_structure_edit(request, pk):
    structure = get_object_or_404(FeeStructure, pk=pk)
    if request.method == 'POST':
        form = FeeStructureForm(request.POST, instance=structure)
        if form.is_valid():
            form.save()
            messages.success(request, "Fee structure updated.")
            return redirect('fees:fee_structure_list')
    else:
        form = FeeStructureForm(instance=structure)
    return render(request, 'fees/fee_structure_form.html', {'form': form, 'title': 'Edit Fee Structure'})

@login_required
@user_passes_test(fee_structure_admin_check)
def fee_structure_delete(request, pk):
    structure = get_object_or_404(FeeStructure, pk=pk)
    if request.method == 'POST':
        structure.delete()
        messages.success(request, "Fee structure deleted.")
        return redirect('fees:fee_structure_list')
    return render(request, 'fees/fee_structure_confirm_delete.html', {'structure': structure})


# -------------------- EXPENDITURES --------------------
@login_required
@user_passes_test(fee_manager_check)
def expenditure_list(request):
    expenditures = Expenditure.objects.select_related('recorded_by').all().order_by('-date')
    return render(request, 'fees/expenditure_list.html', {'expenditures': expenditures})

@login_required
@user_passes_test(fee_manager_check)
def expenditure_add(request):
    if request.method == 'POST':
        form = ExpenditureForm(request.POST, request.FILES)
        if form.is_valid():
            expenditure = form.save(commit=False)
            expenditure.recorded_by = request.user
            expenditure.save()
            messages.success(request, "Expenditure recorded.")
            return redirect('fees:expenditure_list')
    else:
        form = ExpenditureForm()
    return render(request, 'fees/expenditure_form.html', {'form': form, 'title': 'Add Expenditure'})

@login_required
@user_passes_test(fee_manager_check)
def expenditure_edit(request, pk):
    expenditure = get_object_or_404(Expenditure, pk=pk)
    if request.method == 'POST':
        form = ExpenditureForm(request.POST, request.FILES, instance=expenditure)
        if form.is_valid():
            form.save()
            messages.success(request, "Expenditure updated.")
            return redirect('fees:expenditure_list')
    else:
        form = ExpenditureForm(instance=expenditure)
    return render(request, 'fees/expenditure_form.html', {'form': form, 'title': 'Edit Expenditure'})

@login_required
@user_passes_test(fee_manager_check)
def expenditure_delete(request, pk):
    expenditure = get_object_or_404(Expenditure, pk=pk)
    if request.method == 'POST':
        expenditure.delete()
        messages.success(request, "Expenditure deleted.")
        return redirect('fees:expenditure_list')
    return render(request, 'fees/expenditure_confirm_delete.html', {'expenditure': expenditure})


# -------------------- RECORD PAYMENT (GLOBAL) --------------------
@login_required
@user_passes_test(fee_manager_check)
def record_payment(request):
    """Record a new fee payment with student selection."""
    if request.method == 'POST':
        form = RecordPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.recorded_by = request.user
            payment.save()
            student = payment.student
            messages.success(
                request,
                f'Payment of UGX {payment.amount_paid:,.0f} recorded for {student.get_full_name()}. '
                f'Receipt: {payment.receipt_number}',
            )
            return redirect('fees:student_fees', student_id=student.id)
    else:
        form = RecordPaymentForm()
        student_id = request.GET.get('student')
        if student_id:
            try:
                form.fields['student'].initial = int(student_id)
                student = Student.objects.get(pk=student_id)
                if student.current_class:
                    form.fields['fee_structure'].queryset = FeeStructure.objects.filter(
                        class_room=student.current_class
                    )
            except (ValueError, Student.DoesNotExist):
                pass
    return render(request, 'fees/record_payment.html', {'form': form})


# -------------------- PAYMENTS (GLOBAL LIST) --------------------
@login_required
@user_passes_test(fee_manager_check)
def payment_list(request):
    payments = Payment.objects.select_related('student', 'fee_structure').all().order_by('-date_paid')
    student = request.GET.get('student')
    if student:
        payments = payments.filter(
            Q(student__student_id__icontains=student) |
            Q(student__first_name__icontains=student) |
            Q(student__last_name__icontains=student)
        )
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    if from_date:
        payments = payments.filter(date_paid__gte=from_date)
    if to_date:
        payments = payments.filter(date_paid__lte=to_date)
    return render(request, 'fees/payment_list.html', {'payments': payments})


# -------------------- STUDENT-LEVEL PAYMENTS --------------------
@login_required
@user_passes_test(fee_manager_check)
def student_fees(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    payments = student.payments.all().order_by('-date_paid')
    total_due = student.get_total_fees_due()
    total_paid = student.get_total_fees_paid()
    balance = total_due - total_paid
    fee_structures = FeeStructure.objects.filter(
        class_room=student.current_class
    ) if student.current_class else []

    context = {
        'student': student,
        'payments': payments,
        'total_due': total_due,
        'total_paid': total_paid,
        'balance': balance,
        'fee_structures': fee_structures,
    }
    return render(request, 'fees/student_fees.html', context)

@login_required
@user_passes_test(fee_manager_check)
def add_payment(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.student = student
            payment.recorded_by = request.user
            payment.save()
            messages.success(request, f"Payment of UGX {payment.amount_paid} recorded for {student.get_full_name()}.")
            return redirect('fees:student_fees', student_id=student.id)
    else:
        form = PaymentForm()
        if student.current_class:
            form.fields['fee_structure'].queryset = FeeStructure.objects.filter(
                class_room=student.current_class
            )
    return render(request, 'fees/payment_form.html', {'form': form, 'student': student})

@login_required
@user_passes_test(fee_manager_check)
def edit_payment(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    student = payment.student
    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            messages.success(request, "Payment updated successfully.")
            return redirect('fees:student_fees', student_id=student.id)
    else:
        form = PaymentForm(instance=payment)
        if student.current_class:
            form.fields['fee_structure'].queryset = FeeStructure.objects.filter(
                class_room=student.current_class
            )
    return render(request, 'fees/payment_form.html', {'form': form, 'student': student, 'edit': True})

@login_required
@user_passes_test(fee_manager_check)
def delete_payment(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    student = payment.student
    if request.method == 'POST':
        payment.delete()
        messages.success(request, "Payment deleted successfully.")
        return redirect('fees:student_fees', student_id=student.id)
    return render(request, 'fees/payment_confirm_delete.html', {'payment': payment, 'student': student})


# -------------------- PDF EXPORTS --------------------
class PaymentPDFView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.role in ['admin', 'headteacher', 'bursar']

    def get(self, request, *args, **kwargs):
        payments = Payment.objects.select_related('student', 'fee_structure').all().order_by('-date_paid')
        # Apply filters
        student = request.GET.get('student')
        if student:
            payments = payments.filter(
                Q(student__student_id__icontains=student) |
                Q(student__first_name__icontains=student) |
                Q(student__last_name__icontains=student)
            )
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        if from_date:
            payments = payments.filter(date_paid__gte=from_date)
        if to_date:
            payments = payments.filter(date_paid__lte=to_date)

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
        elements.append(Paragraph("Payment List", subtitle_style))
        elements.append(Spacer(1, 0.2 * inch))

        data = [['Student', 'Fee Item', 'Amount', 'Date', 'Receipt', 'Method']]
        for p in payments:
            data.append([
                p.student.get_full_name(),
                p.fee_structure.name if p.fee_structure else 'Other',
                f"UGX {p.amount_paid:,.0f}",
                p.date_paid.strftime('%d-%b-%Y'),
                p.receipt_number,
                p.get_payment_method_display()
            ])

        table = Table(data, repeatRows=1, colWidths=[1.8*inch, 1.5*inch, 1.2*inch, 1.2*inch, 1.5*inch, 1.2*inch])
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
        response['Content-Disposition'] = 'attachment; filename="payments_list.pdf"'
        return response


class ExpenditurePDFView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.role in ['admin', 'headteacher', 'bursar']

    def get(self, request, *args, **kwargs):
        expenditures = Expenditure.objects.select_related('recorded_by').all().order_by('-date')

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
        elements.append(Paragraph("Expenditure List", subtitle_style))
        elements.append(Spacer(1, 0.2 * inch))

        data = [['Date', 'Description', 'Category', 'Amount', 'Recorded By']]
        for e in expenditures:
            # Safely get recorded by name
            recorded_by_name = 'System'
            if e.recorded_by:
                recorded_by_name = e.recorded_by.get_full_name() or e.recorded_by.username

            data.append([
                e.date.strftime('%d-%b-%Y'),
                e.description,
                e.get_category_display(),
                f"UGX {e.amount:,.0f}",
                recorded_by_name
            ])

        table = Table(data, repeatRows=1, colWidths=[1.2*inch, 2.5*inch, 1.5*inch, 1.2*inch, 1.8*inch])
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
        response['Content-Disposition'] = 'attachment; filename="expenditures_list.pdf"'
        return response


# -------------------- COLLECTION REPORT --------------------
@login_required
@user_passes_test(fee_manager_check)
def collection_report(request):
    current_year = AcademicYear.objects.filter(is_current=True).first()
    if not current_year:
        messages.warning(request, "No current academic year set.")
        return redirect('fees:fee_dashboard')
    
    from django.db.models.functions import TruncMonth
    monthly_summary = Payment.objects.filter(
        date_paid__year=timezone.now().year
    ).annotate(month=TruncMonth('date_paid')).values('month').annotate(total=Sum('amount_paid')).order_by('month')
    
    monthly_expenses = Expenditure.objects.filter(
        date__year=timezone.now().year
    ).annotate(month=TruncMonth('date')).values('month').annotate(total=Sum('amount')).order_by('month')
    
    report_data = {}
    for entry in monthly_summary:
        month_str = entry['month'].strftime('%B %Y')
        report_data[month_str] = {'collections': entry['total'], 'expenses': 0}
    for entry in monthly_expenses:
        month_str = entry['month'].strftime('%B %Y')
        if month_str in report_data:
            report_data[month_str]['expenses'] = entry['total']
        else:
            report_data[month_str] = {'collections': 0, 'expenses': entry['total']}
    
    sorted_months = sorted(report_data.keys(), key=lambda x: timezone.datetime.strptime(x, '%B %Y'), reverse=True)
    
    context = {
        'report_data': report_data,
        'sorted_months': sorted_months,
        'current_year': current_year,
    }
    return render(request, 'fees/collection_report.html', context)


@login_required
@portal_module_required('payment_gateway')
def payment_gateway_settings(request):
    return render(request, 'fees/payment_gateway.html', {
        'gateway': get_payment_gateway_status(),
    })


@login_required
@admin_required
def parent_result_access(request):
    """Admin: toggle fee-balance result restriction and manage per-student overrides."""
    portal_settings = SchoolPortalSettings.get_solo()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save_policy':
            policy_form = ParentResultsPolicyForm(request.POST)
            if policy_form.is_valid():
                portal_settings.block_parent_results_on_fee_balance = policy_form.cleaned_data[
                    'block_parent_results_on_fee_balance'
                ]
                portal_settings.save()
                messages.success(request, 'Parent results policy updated.')
            return redirect('fees:parent_result_access')
        if action == 'save_overrides':
            student_ids = [int(k.split('_')[1]) for k in request.POST if k.startswith('override_')]
            students = Student.objects.filter(pk__in=student_ids, is_active=True)
            for student in students:
                key = f'override_{student.pk}'
                value = request.POST.get(key, 'default')
                if value in dict(Student.PARENT_RESULTS_ACCESS_CHOICES):
                    student.parent_results_access = value
                    student.save(update_fields=['parent_results_access'])
            messages.success(request, 'Student result access overrides saved.')
            return redirect(request.get_full_path())

    policy_form = ParentResultsPolicyForm(
        initial={
            'block_parent_results_on_fee_balance': portal_settings.block_parent_results_on_fee_balance,
        }
    )

    students = Student.objects.filter(is_active=True).select_related(
        'parent', 'current_class'
    ).order_by('last_name', 'first_name')

    search = request.GET.get('search', '').strip()
    balance_filter = request.GET.get('balance', '')
    access_filter = request.GET.get('access', '')
    class_filter = request.GET.get('class', '')

    if search:
        students = students.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(student_id__icontains=search)
            | Q(parent__username__icontains=search)
            | Q(parent__first_name__icontains=search)
            | Q(parent__last_name__icontains=search)
        )
    if class_filter:
        students = students.filter(current_class_id=class_filter)

    rows = []
    for student in students:
        balance = student.get_fees_balance()
        can_view = parent_can_view_results(student)
        rows.append({
            'student': student,
            'balance': balance,
            'can_view': can_view,
            'access_label': effective_access_label(student),
        })

    if balance_filter == 'owing':
        rows = [r for r in rows if r['balance'] > 0]
    elif balance_filter == 'clear':
        rows = [r for r in rows if r['balance'] <= 0]

    if access_filter == 'blocked':
        rows = [r for r in rows if not r['can_view']]
    elif access_filter == 'allowed':
        rows = [r for r in rows if r['can_view']]

    class_list = ClassRoom.objects.all().order_by('name')

    return render(request, 'fees/parent_result_access.html', {
        'policy_form': policy_form,
        'portal_settings': portal_settings,
        'rows': rows,
        'class_list': class_list,
        'search': search,
        'balance_filter': balance_filter,
        'access_filter': access_filter,
        'class_filter': class_filter,
        'blocked_count': sum(1 for r in rows if not r['can_view']),
        'owing_count': sum(1 for r in rows if r['balance'] > 0),
    })