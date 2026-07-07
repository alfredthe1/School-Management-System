from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Avg
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from django.db import transaction as db_transaction
import json

from school.security import mobile_money_callback_view

from students.models import Student
from examinations.models import ExamResult
from fees.models import Payment, FeeStructure, MobileMoneyTransaction
from fees.mobile_money import (
    UgandaMobileMoneyClient,
    MobileMoneyAPIError,
    parse_mtn_callback,
    parse_airtel_callback,
)
from academics.models import StudentResult
from core.models import AcademicYear
from announcements.models import Announcement
from django.conf import settings
from core.parent_results_access import parent_can_view_results, parent_results_blocked_reason
from fees.payment_config import get_payment_gateway_status
from communication.models import Notification
from .decorators import parent_module_required, get_parent_child
from .forms import LinkChildForm, ParentMobileMoneyPaymentForm


def _payment_method_for_provider(provider):
    return 'mtn_momo' if provider == 'mtn' else 'airtel_money'


def _notify_payment_complete(transaction, payment):
    """In-app receipt for the parent after a successful mobile money payment."""
    Notification.objects.create(
        sender=transaction.parent,
        recipient=transaction.parent,
        title=f'Payment received — {transaction.student.get_full_name()}',
        message=(
            f'Your {transaction.provider_label} payment of UGX {transaction.amount:,.0f} '
            f'for {transaction.student.get_full_name()} was successful. '
            f'School receipt: {payment.receipt_number}.'
        ),
        notification_type='fee',
        priority='high',
    )


def _complete_simulated_payment(transaction):
    """Record payment immediately when APIs are not configured (demo mode)."""
    transaction.status = 'completed'
    transaction.transaction_reference = f'SIM-{transaction.id:06d}'
    transaction.result_description = (
        f'Simulated {transaction.provider_label} payment (API not configured)'
    )
    payment = Payment.objects.create(
        student=transaction.student,
        fee_structure=transaction.fee_structure,
        amount_paid=transaction.amount,
        payment_method=_payment_method_for_provider(transaction.provider),
        remarks=f'Simulated {transaction.provider_label} by {transaction.parent.username}',
        recorded_by=transaction.parent,
    )
    transaction.payment = payment
    transaction.save()
    _notify_payment_complete(transaction, payment)
    return payment


@login_required
@parent_module_required('parent_dashboard')
def parent_dashboard(request):
    children = Student.objects.filter(parent=request.user, is_active=True).select_related('current_class')
    children_data = []
    current_year = AcademicYear.objects.filter(is_current=True).first()

    for child in children:
        can_view_results = parent_can_view_results(child)
        exam_avg = None
        recent_results = []
        if can_view_results:
            exam_avg = ExamResult.objects.filter(
                student=child, exam__is_published=True
            ).aggregate(avg=Avg('marks_obtained'))['avg']
            recent_results = list(
                ExamResult.objects.filter(
                    student=child, exam__is_published=True
                ).select_related('exam', 'exam__subject').order_by('-exam__start_date')[:3]
            )
        total_due = child.get_total_fees_due()
        total_paid = child.get_total_fees_paid()
        children_data.append({
            'student': child,
            'can_view_results': can_view_results,
            'results_blocked_reason': parent_results_blocked_reason(child),
            'exam_avg': round(exam_avg, 1) if exam_avg else None,
            'balance': child.get_fees_balance(),
            'total_due': total_due,
            'total_paid': total_paid,
            'recent_results': recent_results,
        })

    announcements = Announcement.objects.filter(is_active=True).order_by('-created_at')[:5]
    pending_payments = MobileMoneyTransaction.objects.filter(
        parent=request.user, status='pending'
    ).select_related('student')[:5]

    return render(request, 'parents/dashboard.html', {
        'children_data': children_data,
        'announcements': announcements,
        'pending_payments': pending_payments,
        'current_year': current_year,
    })


@login_required
@parent_module_required('parent_children')
def my_children(request):
    children = Student.objects.filter(parent=request.user, is_active=True).select_related('current_class')
    return render(request, 'parents/children_list.html', {'children': children})


@login_required
@parent_module_required('parent_progress')
def child_progress(request, student_id):
    student = get_parent_child(request, student_id)
    can_view_results = parent_can_view_results(student)
    exam_results = []
    continuous_results = []
    if can_view_results:
        exam_results = ExamResult.objects.filter(
            student=student, exam__is_published=True
        ).select_related('exam', 'exam__subject', 'exam__term').order_by('-exam__start_date')
        continuous_results = StudentResult.objects.filter(student=student).select_related(
            'subject', 'term'
        ).order_by('-term__name')
    payments = Payment.objects.filter(student=student).order_by('-date_paid')
    total_due = student.get_total_fees_due()
    total_paid = student.get_total_fees_paid()
    balance = student.get_fees_balance()

    return render(request, 'parents/child_progress.html', {
        'student': student,
        'can_view_results': can_view_results,
        'results_blocked_reason': parent_results_blocked_reason(student),
        'exam_results': exam_results,
        'continuous_results': continuous_results,
        'payments': payments,
        'total_due': total_due,
        'total_paid': total_paid,
        'balance': balance,
    })


@login_required
@parent_module_required('parent_pay_fees')
def pay_fees_hub(request):
    children = Student.objects.filter(parent=request.user, is_active=True).select_related('current_class')
    children_data = []
    for child in children:
        children_data.append({
            'student': child,
            'total_due': child.get_total_fees_due(),
            'total_paid': child.get_total_fees_paid(),
            'balance': child.get_fees_balance(),
        })
    return render(request, 'parents/pay_fees_hub.html', {'children_data': children_data})


@login_required
@parent_module_required('parent_link_child')
def link_child(request):
    if request.method == 'POST':
        form = LinkChildForm(request.POST)
        if form.is_valid():
            student = form.cleaned_data['student']
            student.parent = request.user
            student.save()
            messages.success(request, f'Successfully linked {student.get_full_name()} to your account.')
            return redirect('parents:dashboard')
    else:
        form = LinkChildForm()
    return render(request, 'parents/link_child.html', {'form': form})


@login_required
@parent_module_required('parent_pay_fees')
def pay_fees(request, student_id):
    student = get_parent_child(request, student_id)
    form = ParentMobileMoneyPaymentForm(request.POST or None, student=student, parent=request.user)

    if request.method == 'POST' and form.is_valid():
        fee_structure = form.cleaned_data['fee_structure']
        amount = form.cleaned_data['amount']
        phone = form.cleaned_data['phone_number']
        provider = form.cleaned_data['provider']
        balance = student.get_fees_balance()

        if amount > balance and balance > 0:
            messages.warning(request, f'Amount exceeds outstanding balance of UGX {balance:,.0f}.')
            return redirect('parents:pay_fees', student_id=student.id)

        min_amt = getattr(settings, 'MOBILE_MONEY_MIN_AMOUNT', 500)
        max_amt = getattr(settings, 'MOBILE_MONEY_MAX_AMOUNT', 10_000_000)
        if amount < min_amt:
            messages.warning(request, f'Minimum payment is UGX {min_amt:,.0f}.')
            return redirect('parents:pay_fees', student_id=student.id)
        if amount > max_amt:
            messages.warning(request, f'Maximum payment is UGX {max_amt:,.0f}.')
            return redirect('parents:pay_fees', student_id=student.id)

        if not getattr(settings, 'MOBILE_MONEY_ENABLED', True):
            messages.error(request, 'Mobile money payments are temporarily disabled. Contact the school.')
            return redirect('parents:pay_fees', student_id=student.id)

        transaction = MobileMoneyTransaction.objects.create(
            student=student,
            parent=request.user,
            fee_structure=fee_structure,
            provider=provider,
            amount=amount,
            phone_number=phone,
            status='pending',
        )

        client = UgandaMobileMoneyClient(provider=provider)
        if client.is_configured():
            try:
                result = client.request_payment(
                    phone=phone,
                    amount=amount,
                    account_reference=student.student_id,
                    description=f'School fees {student.student_id}',
                )
                transaction.reference_id = result.get('reference_id', '')
                transaction.external_id = result.get('external_id', '')
                transaction.result_description = result.get('message', '')
                transaction.save()
                messages.info(
                    request,
                    f'Payment request sent to your {client.provider_label} number. '
                    f'Approve the prompt on your phone to complete payment.',
                )
                return redirect('parents:payment_status', transaction_id=transaction.id)
            except MobileMoneyAPIError as e:
                transaction.status = 'failed'
                transaction.result_description = str(e)
                transaction.save()
                messages.error(request, f'{client.provider_label} request failed: {e}')
        else:
            payment = _complete_simulated_payment(transaction)
            messages.success(
                request,
                f'Payment of UGX {amount:,.0f} recorded via {transaction.provider_label} '
                f'(simulation mode). Receipt: {payment.receipt_number}',
            )
            return redirect('parents:child_progress', student_id=student.id)

    fee_structures = FeeStructure.objects.filter(class_room=student.current_class)
    current_year = AcademicYear.objects.filter(is_current=True).first()
    if current_year:
        fee_structures = fee_structures.filter(academic_year=current_year)

    gateway = get_payment_gateway_status()
    mtn_configured = gateway['mtn_ready']
    airtel_configured = gateway['airtel_ready']

    return render(request, 'parents/pay_fees.html', {
        'student': student,
        'form': form,
        'balance': student.get_fees_balance(),
        'total_paid': student.get_total_fees_paid(),
        'total_due': student.get_total_fees_due(),
        'fee_structures': fee_structures,
        'mtn_configured': mtn_configured,
        'airtel_configured': airtel_configured,
        'mobile_money_configured': mtn_configured or airtel_configured,
        'gateway': gateway,
    })


@login_required
@parent_module_required('parent_pay_fees')
def payment_status(request, transaction_id):
    transaction = get_object_or_404(
        MobileMoneyTransaction, id=transaction_id, parent=request.user
    )
    return render(request, 'parents/payment_status.html', {'transaction': transaction})


@login_required
@parent_module_required('parent_pay_fees')
def payment_status_poll(request, transaction_id):
    transaction = get_object_or_404(
        MobileMoneyTransaction.objects.select_related('student', 'payment', 'fee_structure'),
        id=transaction_id,
        parent=request.user,
    )
    data = {
        'status': transaction.status,
        'receipt': transaction.transaction_reference,
        'school_receipt': transaction.payment.receipt_number if transaction.payment_id else '',
        'description': transaction.result_description,
        'provider': transaction.provider,
        'provider_label': transaction.provider_label,
        'amount': str(transaction.amount),
        'student_name': transaction.student.get_full_name(),
        'phone_masked': transaction.phone_number[-4:].rjust(len(transaction.phone_number), '*') if transaction.phone_number else '',
    }
    return JsonResponse(data)


@login_required
@parent_module_required('parent_payment_history')
def payment_history(request):
    children = Student.objects.filter(parent=request.user, is_active=True)
    child_ids = children.values_list('id', flat=True)

    payments = Payment.objects.filter(student_id__in=child_ids).select_related(
        'student', 'fee_structure'
    ).order_by('-date_paid', '-id')

    mobile_txns = MobileMoneyTransaction.objects.filter(
        parent=request.user
    ).select_related('student', 'payment', 'fee_structure').order_by('-created_at')

    return render(request, 'parents/payment_history.html', {
        'payments': payments[:50],
        'mobile_transactions': mobile_txns[:50],
        'children': children,
        'gateway': get_payment_gateway_status(),
    })


@login_required
@parent_module_required('parent_payment_history')
def payment_record_detail(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related('student', 'fee_structure'),
        id=payment_id,
        student__parent=request.user,
    )
    mm_txn = getattr(payment, 'mobile_money_transaction', None)
    return render(request, 'parents/payment_record_detail.html', {
        'payment': payment,
        'mm_txn': mm_txn,
    })


def _handle_mobile_money_callback(request, provider):
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    if provider == 'mtn':
        result = parse_mtn_callback(payload)
    else:
        result = parse_airtel_callback(payload)

    reference_id = result.get('reference_id')
    if not reference_id:
        return HttpResponse(status=400)

    with db_transaction.atomic():
        transaction = (
            MobileMoneyTransaction.objects.select_for_update()
            .filter(reference_id=reference_id)
            .first()
        )

        if not transaction:
            return JsonResponse({'status': 'accepted'})

        # Idempotency: ignore duplicate success/failure notifications
        if transaction.status in ('completed', 'failed'):
            return JsonResponse({'status': 'accepted'})

        if result['success']:
            payment = Payment.objects.create(
                student=transaction.student,
                fee_structure=transaction.fee_structure,
                amount_paid=transaction.amount,
                payment_method=_payment_method_for_provider(transaction.provider),
                remarks=f'{transaction.provider_label} ref: {result["transaction_reference"]}',
                recorded_by=transaction.parent,
            )
            transaction.status = 'completed'
            transaction.transaction_reference = result['transaction_reference']
            transaction.payment = payment
            transaction.result_description = result['result_desc']
            _notify_payment_complete(transaction, payment)
        else:
            transaction.status = 'failed'
            transaction.result_description = result['result_desc']

        transaction.save()

    return JsonResponse({'status': 'accepted'})


@mobile_money_callback_view
@require_POST
def mtn_callback(request):
    """MTN Mobile Money (MoMo) collection callback."""
    return _handle_mobile_money_callback(request, 'mtn')


@mobile_money_callback_view
@require_POST
def airtel_callback(request):
    """Airtel Money payment callback."""
    return _handle_mobile_money_callback(request, 'airtel')