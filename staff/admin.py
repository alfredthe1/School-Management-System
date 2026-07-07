from django.contrib import admin

from .models import (
    PayrollAllowanceLine,
    PayrollItem,
    PayrollRun,
    SalaryPayment,
    StaffAllowance,
    StaffMember,
)


class StaffAllowanceInline(admin.TabularInline):
    model = StaffAllowance
    extra = 1


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'get_full_name', 'job_title', 'department', 'base_salary', 'is_active')
    list_filter = ('department', 'employment_type', 'is_active')
    search_fields = ('first_name', 'last_name', 'employee_id', 'job_title')
    inlines = [StaffAllowanceInline]


@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = ('year', 'month', 'status', 'total_amount', 'processed_at')
    list_filter = ('status', 'year')


@admin.register(SalaryPayment)
class SalaryPaymentAdmin(admin.ModelAdmin):
    list_display = ('staff', 'amount_paid', 'payment_date', 'payment_method', 'reference')
    list_filter = ('payment_method', 'payment_date')