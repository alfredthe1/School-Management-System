from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class StaffMember(models.Model):
    DEPARTMENT_CHOICES = [
        ('administration', 'Administration'),
        ('academics', 'Academics'),
        ('finance', 'Finance'),
        ('support', 'Support Services'),
    ]
    EMPLOYMENT_TYPES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='staff_profile',
    )
    employee_id = models.CharField(max_length=20, unique=True, blank=True, editable=False)
    job_title = models.CharField(max_length=100)
    department = models.CharField(max_length=30, choices=DEPARTMENT_CHOICES, default='academics')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[('M', 'Male'), ('F', 'Female')],
        blank=True,
    )
    qualification = models.CharField(max_length=200, blank=True)
    date_joined = models.DateField(default=timezone.now)
    employment_type = models.CharField(
        max_length=20, choices=EMPLOYMENT_TYPES, default='full_time',
    )
    base_salary = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text='Monthly base salary in UGX',
    )
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account = models.CharField(max_length=50, blank=True)
    profile_pic = models.ImageField(upload_to='staff_photos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f'{self.get_full_name()} ({self.employee_id})'

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def save(self, *args, **kwargs):
        if not self.employee_id:
            year = timezone.now().strftime('%Y')
            last = StaffMember.objects.filter(
                employee_id__startswith=f'STF/{year}/'
            ).order_by('employee_id').last()
            if last:
                new_number = int(last.employee_id.split('/')[-1]) + 1
            else:
                new_number = 1
            self.employee_id = f'STF/{year}/{new_number:03d}'
        super().save(*args, **kwargs)

    def get_active_allowances(self):
        return self.allowances.filter(is_active=True)

    def get_monthly_allowances_total(self):
        total = self.get_active_allowances().aggregate(total=Sum('amount'))['total']
        return total or Decimal('0')

    def get_projected_monthly_pay(self):
        return self.base_salary + self.get_monthly_allowances_total()

    @property
    def role_display(self):
        return self.user.get_role_display()


class StaffAllowance(models.Model):
    staff = models.ForeignKey(
        StaffMember, on_delete=models.CASCADE, related_name='allowances',
    )
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} — UGX {self.amount:,.0f}'


class PayrollRun(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('processed', 'Processed'),
        ('paid', 'Paid'),
    ]
    month = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payroll_runs_processed',
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-year', '-month']
        unique_together = ['month', 'year']

    def __str__(self):
        return f'Payroll {self.get_month_display()} {self.year}'

    def get_month_display(self):
        import calendar
        return calendar.month_name[self.month]

    def recalculate_total(self):
        total = self.items.aggregate(total=Sum('net_pay'))['total'] or Decimal('0')
        self.total_amount = total
        self.save(update_fields=['total_amount'])


class PayrollItem(models.Model):
    payroll_run = models.ForeignKey(
        PayrollRun, on_delete=models.CASCADE, related_name='items',
    )
    staff = models.ForeignKey(
        StaffMember, on_delete=models.CASCADE, related_name='payroll_items',
    )
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['payroll_run', 'staff']
        ordering = ['staff__last_name']

    def __str__(self):
        return f'{self.staff} — {self.payroll_run}'

    def save(self, *args, **kwargs):
        self.net_pay = self.base_salary + self.total_allowances - self.deductions
        super().save(*args, **kwargs)


class PayrollAllowanceLine(models.Model):
    payroll_item = models.ForeignKey(
        PayrollItem, on_delete=models.CASCADE, related_name='allowance_lines',
    )
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)


class SalaryPayment(models.Model):
    PAYMENT_METHODS = [
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('mobile', 'Mobile Money'),
    ]
    staff = models.ForeignKey(
        StaffMember, on_delete=models.CASCADE, related_name='salary_payments',
    )
    payroll_item = models.ForeignKey(
        PayrollItem, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='payments',
    )
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='bank')
    reference = models.CharField(max_length=100, blank=True)
    remarks = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date', '-created_at']

    def __str__(self):
        return f'{self.staff} — UGX {self.amount_paid:,.0f}'