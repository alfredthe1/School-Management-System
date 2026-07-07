"""Demo staff members and payroll seeding."""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from staff.models import PayrollRun, SalaryPayment, StaffAllowance, StaffMember
from staff.payroll_utils import generate_payroll
from teachers.models import Teacher

User = get_user_model()


def _add_allowances(staff, allowance_list):
    for name, amount, description in allowance_list:
        StaffAllowance.objects.get_or_create(
            staff=staff,
            name=name,
            defaults={
                'amount': Decimal(str(amount)),
                'description': description,
                'is_active': True,
            },
        )


def _ensure_staff(user, defaults, allowances=None):
    staff, created = StaffMember.objects.get_or_create(
        user=user,
        defaults=defaults,
    )
    if not created:
        for key, value in defaults.items():
            setattr(staff, key, value)
        staff.save()
    if allowances:
        _add_allowances(staff, allowances)
    return staff


def staff_from_teacher(teacher, base_salary, extra_allowances=None):
    """Create or update a StaffMember from an existing Teacher record."""
    user = teacher.user
    subject_names = ', '.join(s.name for s in teacher.subjects_taught.all()[:3])
    job_title = f'Teacher — {subject_names}' if subject_names else 'Class Teacher'

    defaults = {
        'first_name': teacher.first_name,
        'last_name': teacher.last_name,
        'job_title': job_title,
        'department': 'academics',
        'date_of_birth': teacher.date_of_birth,
        'gender': teacher.gender or 'F',
        'qualification': teacher.qualification or 'Bachelor of Education',
        'date_joined': teacher.date_joined,
        'employment_type': 'full_time',
        'base_salary': Decimal(str(base_salary)),
        'phone': teacher.phone or '+256700000000',
        'email': teacher.email or user.email,
        'address': teacher.address or 'Kampala, Uganda',
        'bank_name': 'Stanbic Bank',
        'bank_account': f'100{teacher.pk:06d}',
        'is_active': teacher.is_active,
    }
    allowances = [
        ('Transport Allowance', 150000, 'Monthly transport'),
        ('Housing Allowance', 200000, 'Monthly housing support'),
    ]
    if extra_allowances:
        allowances.extend(extra_allowances)
    return _ensure_staff(user, defaults, allowances)


def populate_staff_and_payroll(stdout=None):
    """Seed staff profiles (including all teachers) and demo payroll runs."""
    write = stdout.write if stdout else print

    # Bursar account
    bursar_user, _ = User.objects.get_or_create(
        username='bursar',
        defaults={
            'email': 'bursar@happychild.ac.ug',
            'role': 'bursar',
            'first_name': 'Sarah',
            'last_name': 'Nakato',
        },
    )
    if not bursar_user.check_password('bursar123'):
        bursar_user.set_password('bursar123')
        bursar_user.save()

    _ensure_staff(
        bursar_user,
        {
            'first_name': 'Sarah',
            'last_name': 'Nakato',
            'job_title': 'School Bursar',
            'department': 'finance',
            'gender': 'F',
            'qualification': 'Bachelor of Commerce',
            'date_joined': date(2024, 1, 15),
            'employment_type': 'full_time',
            'base_salary': Decimal('1800000'),
            'phone': '+256712345001',
            'email': 'bursar@happychild.ac.ug',
            'address': 'Kampala, Uganda',
            'bank_name': 'Centenary Bank',
            'bank_account': '3200456789',
            'is_active': True,
        },
        [
            ('Transport Allowance', 150000, 'Monthly transport'),
            ('Responsibility Allowance', 100000, 'Finance office duties'),
        ],
    )
    write('  Bursar staff profile ready (bursar / bursar123)')

    # Head teacher
    try:
        head_user = User.objects.get(username='headteacher')
        _ensure_staff(
            head_user,
            {
                'first_name': head_user.first_name or 'John',
                'last_name': head_user.last_name or 'Okello',
                'job_title': 'Head Teacher',
                'department': 'administration',
                'gender': 'M',
                'qualification': 'Master of Education',
                'date_joined': date(2020, 2, 1),
                'employment_type': 'full_time',
                'base_salary': Decimal('2500000'),
                'phone': '+256712345002',
                'email': head_user.email,
                'address': 'Kampala, Uganda',
                'bank_name': 'DFCU Bank',
                'bank_account': '0100987654',
                'is_active': True,
            },
            [
                ('Housing Allowance', 500000, 'Head teacher housing'),
                ('Transport Allowance', 200000, 'Monthly transport'),
                ('Responsibility Allowance', 300000, 'School leadership'),
            ],
        )
        write('  Head teacher staff profile ready')
    except User.DoesNotExist:
        write('  Head teacher user not found — skipped')

    # All teachers as staff members
    teacher_salaries = {
        'teacher1': 1500000,
        'teacher2': 1400000,
        'teacher3': 1300000,
    }
    teacher_count = 0
    for teacher in Teacher.objects.select_related('user').prefetch_related('subjects_taught'):
        username = teacher.user.username
        salary = teacher_salaries.get(username, 1200000)
        extra = []
        if username == 'teacher1':
            extra = [('Subject Head Allowance', 100000, 'Mathematics department lead')]
        staff_from_teacher(teacher, salary, extra_allowances=extra or None)
        teacher_count += 1
        write(f'  Staff profile for teacher: {teacher.get_full_name()} ({teacher.user.username})')

    if teacher_count == 0:
        write('  No teachers found — run populate_demo_data first or add teachers manually')

    # Payroll runs
    today = timezone.now().date()
    month, year = today.month, today.year
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1

    admin_user = User.objects.filter(role='admin').first()

    # Previous month — processed and paid with sample payments
    prev_run = PayrollRun.objects.filter(month=prev_month, year=prev_year).first()
    if prev_run and prev_run.status == 'paid':
        write(f'  Payroll {prev_run.get_month_display()} {prev_year} already paid — skipping regeneration')
    else:
        prev_run = generate_payroll(prev_month, prev_year, processed_by=admin_user)
        prev_run.status = 'paid'
        prev_run.save()
    for item in prev_run.items.select_related('staff'):
        SalaryPayment.objects.get_or_create(
            staff=item.staff,
            payroll_item=item,
            payment_date=date(prev_year, prev_month, 28),
            defaults={
                'amount_paid': item.net_pay,
                'payment_method': 'bank',
                'reference': f'SAL-{prev_year}{prev_month:02d}-{item.staff.employee_id}',
                'remarks': f'Demo salary payment for {prev_run.get_month_display()} {prev_year}',
                'recorded_by': admin_user,
            },
        )
    write(
        f'  Payroll {prev_run.get_month_display()} {prev_year}: '
        f'{prev_run.items.count()} staff, UGX {prev_run.total_amount:,.0f} (paid)'
    )

    # Current month — processed, awaiting payment
    current_run = generate_payroll(month, year, processed_by=admin_user)
    write(
        f'  Payroll {current_run.get_month_display()} {year}: '
        f'{current_run.items.count()} staff, UGX {current_run.total_amount:,.0f} (processed)'
    )

    total_staff = StaffMember.objects.filter(is_active=True).count()
    write(f'  Total active staff members: {total_staff}')
    return total_staff