from decimal import Decimal

from django.utils import timezone

from .models import PayrollAllowanceLine, PayrollItem, PayrollRun, StaffMember


def generate_payroll(month, year, processed_by=None):
    """Generate or refresh payroll items for all active staff."""
    run, _ = PayrollRun.objects.get_or_create(month=month, year=year)
    if run.status == 'paid':
        raise ValueError('This payroll has already been marked as paid and cannot be regenerated.')

    active_staff = StaffMember.objects.filter(is_active=True)
    for staff in active_staff:
        allowances = staff.get_active_allowances()
        allowance_total = staff.get_monthly_allowances_total()

        item, _ = PayrollItem.objects.update_or_create(
            payroll_run=run,
            staff=staff,
            defaults={
                'base_salary': staff.base_salary,
                'total_allowances': allowance_total,
                'deductions': Decimal('0'),
            },
        )
        item.allowance_lines.all().delete()
        for allowance in allowances:
            PayrollAllowanceLine.objects.create(
                payroll_item=item,
                name=allowance.name,
                amount=allowance.amount,
            )
        item.net_pay = item.base_salary + item.total_allowances - item.deductions
        item.save()

    # Remove items for staff no longer active
    PayrollItem.objects.filter(payroll_run=run).exclude(
        staff__in=active_staff
    ).delete()

    run.recalculate_total()
    if processed_by and run.status == 'draft':
        run.processed_by = processed_by
        run.processed_at = timezone.now()
        run.status = 'processed'
        run.save()
    return run


def get_current_payroll_period():
    today = timezone.now().date()
    return today.month, today.year