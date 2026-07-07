from accounts.decorators import portal_module_required
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import (
    PayrollItemEditForm,
    SalaryPaymentForm,
    StaffAllowanceForm,
    StaffMemberForm,
)
from .models import PayrollItem, PayrollRun, SalaryPayment, StaffAllowance, StaffMember
from .payroll_utils import generate_payroll, get_current_payroll_period


def staff_manager_check(user):
    from accounts.permission_utils import user_can_access
    return user.is_authenticated and user_can_access(user, 'staff_payroll')


def has_staff_profile(user):
    return user.is_authenticated and hasattr(user, 'staff_profile')


# -------------------- STAFF CRUD --------------------

class StaffListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = StaffMember
    template_name = 'staff/staff_list.html'
    context_object_name = 'staff_members'

    def test_func(self):
        return staff_manager_check(self.request.user)

    def get_queryset(self):
        qs = StaffMember.objects.select_related('user').all()
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(employee_id__icontains=search) |
                Q(job_title__icontains=search)
            )
        dept = self.request.GET.get('department')
        if dept:
            qs = qs.filter(department=dept)
        role = self.request.GET.get('role')
        if role:
            qs = qs.filter(user__role=role)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['departments'] = StaffMember.DEPARTMENT_CHOICES
        return ctx


class StaffDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = StaffMember
    template_name = 'staff/staff_detail.html'
    context_object_name = 'staff'

    def test_func(self):
        return staff_manager_check(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        staff = self.object
        ctx['allowances'] = staff.allowances.all()
        ctx['monthly_gross'] = staff.get_projected_monthly_pay()
        ctx['recent_payments'] = staff.salary_payments.all()[:10]
        return ctx


class StaffCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = StaffMember
    form_class = StaffMemberForm
    template_name = 'staff/staff_form.html'
    success_url = reverse_lazy('staff:list')

    def test_func(self):
        return staff_manager_check(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add Staff Member'
        return ctx

    def form_valid(self, form):
        messages.success(
            self.request,
            f'Staff {form.instance.get_full_name()} added with ID {form.instance.employee_id}.',
        )
        return super().form_valid(form)


class StaffUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = StaffMember
    form_class = StaffMemberForm
    template_name = 'staff/staff_form.html'
    success_url = reverse_lazy('staff:list')

    def test_func(self):
        return staff_manager_check(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Staff: {self.object.get_full_name()}'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Staff record updated successfully.')
        return super().form_valid(form)


class StaffDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = StaffMember
    template_name = 'staff/staff_confirm_delete.html'
    success_url = reverse_lazy('staff:list')

    def test_func(self):
        return self.request.user.role == 'admin'

    def delete(self, request, *args, **kwargs):
        staff = self.get_object()
        name = staff.get_full_name()
        staff.delete()
        messages.success(request, f'Staff record for {name} removed.')
        return redirect(self.success_url)


# -------------------- ALLOWANCES --------------------

@login_required
@user_passes_test(staff_manager_check)
def manage_allowances(request, pk):
    staff = get_object_or_404(StaffMember, pk=pk)
    form = StaffAllowanceForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            allowance = form.save(commit=False)
            allowance.staff = staff
            allowance.save()
            messages.success(request, f'Allowance "{allowance.name}" added.')
            return redirect('staff:allowances', pk=staff.pk)

    return render(request, 'staff/staff_allowances.html', {
        'staff': staff,
        'allowances': staff.allowances.all(),
        'form': form,
        'monthly_total': staff.get_monthly_allowances_total(),
        'projected_pay': staff.get_projected_monthly_pay(),
    })


@login_required
@user_passes_test(staff_manager_check)
def toggle_allowance(request, pk, allowance_id):
    staff = get_object_or_404(StaffMember, pk=pk)
    allowance = get_object_or_404(StaffAllowance, pk=allowance_id, staff=staff)
    allowance.is_active = not allowance.is_active
    allowance.save()
    status = 'activated' if allowance.is_active else 'deactivated'
    messages.success(request, f'Allowance "{allowance.name}" {status}.')
    return redirect('staff:allowances', pk=staff.pk)


@login_required
@user_passes_test(staff_manager_check)
def delete_allowance(request, pk, allowance_id):
    staff = get_object_or_404(StaffMember, pk=pk)
    allowance = get_object_or_404(StaffAllowance, pk=allowance_id, staff=staff)
    if request.method == 'POST':
        name = allowance.name
        allowance.delete()
        messages.success(request, f'Allowance "{name}" deleted.')
    return redirect('staff:allowances', pk=staff.pk)


# -------------------- PAYROLL (ADMIN) --------------------

@login_required
@user_passes_test(staff_manager_check)
def payroll_dashboard(request):
    month, year = get_current_payroll_period()
    runs = PayrollRun.objects.all()[:12]
    current_run = PayrollRun.objects.filter(month=month, year=year).first()
    active_staff = StaffMember.objects.filter(is_active=True).count()
    total_monthly_commitment = sum(
        s.get_projected_monthly_pay() for s in StaffMember.objects.filter(is_active=True)
    )

    return render(request, 'staff/payroll_dashboard.html', {
        'runs': runs,
        'current_run': current_run,
        'current_month': month,
        'current_year': year,
        'active_staff': active_staff,
        'total_monthly_commitment': total_monthly_commitment,
    })


@login_required
@user_passes_test(staff_manager_check)
def generate_payroll_view(request):
    month = int(request.POST.get('month', timezone.now().month))
    year = int(request.POST.get('year', timezone.now().year))
    run = None
    try:
        run = generate_payroll(month, year, processed_by=request.user)
        messages.success(
            request,
            f'Payroll for {run.get_month_display()} {year} generated — '
            f'{run.items.count()} staff, total UGX {run.total_amount:,.0f}.',
        )
        return redirect('staff:payroll_detail', pk=run.pk)
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect('staff:payroll_dashboard')


@login_required
@user_passes_test(staff_manager_check)
def payroll_detail(request, pk):
    run = get_object_or_404(PayrollRun, pk=pk)
    items = run.items.select_related('staff', 'staff__user').prefetch_related('allowance_lines')
    return render(request, 'staff/payroll_detail.html', {
        'run': run,
        'items': items,
    })


@login_required
@user_passes_test(staff_manager_check)
def edit_payroll_item(request, pk):
    item = get_object_or_404(PayrollItem, pk=pk)
    if request.method == 'POST':
        form = PayrollItemEditForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            item.payroll_run.recalculate_total()
            messages.success(request, 'Payroll item updated.')
            return redirect('staff:payroll_detail', pk=item.payroll_run.pk)
    else:
        form = PayrollItemEditForm(instance=item)
    return render(request, 'staff/payroll_item_edit.html', {
        'form': form,
        'item': item,
    })


@login_required
@user_passes_test(staff_manager_check)
def mark_payroll_paid(request, pk):
    run = get_object_or_404(PayrollRun, pk=pk)
    if request.method == 'POST':
        run.status = 'paid'
        run.save()
        messages.success(request, f'Payroll for {run.get_month_display()} {run.year} marked as paid.')
    return redirect('staff:payroll_detail', pk=run.pk)


@login_required
@user_passes_test(staff_manager_check)
def record_salary_payment(request, staff_pk):
    staff = get_object_or_404(StaffMember, pk=staff_pk)
    payroll_item = None
    item_id = request.GET.get('item')
    if item_id:
        payroll_item = get_object_or_404(PayrollItem, pk=item_id, staff=staff)

    if request.method == 'POST':
        form = SalaryPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.staff = staff
            payment.payroll_item = payroll_item
            payment.recorded_by = request.user
            payment.save()
            messages.success(request, f'Payment of UGX {payment.amount_paid:,.0f} recorded.')
            if payroll_item:
                return redirect('staff:payroll_detail', pk=payroll_item.payroll_run.pk)
            return redirect('staff:detail', pk=staff.pk)
    else:
        initial = {}
        if payroll_item:
            paid_so_far = payroll_item.payments.aggregate(
                total=Sum('amount_paid')
            )['total'] or 0
            initial['amount_paid'] = payroll_item.net_pay - paid_so_far
        form = SalaryPaymentForm(initial=initial)

    return render(request, 'staff/salary_payment_form.html', {
        'form': form,
        'staff': staff,
        'payroll_item': payroll_item,
    })


# -------------------- MY PAYROLL (STAFF SELF-SERVICE) --------------------

@login_required
@portal_module_required('my_payroll')
@user_passes_test(has_staff_profile)
def my_payroll(request):
    staff = request.user.staff_profile
    month, year = get_current_payroll_period()
    current_item = PayrollItem.objects.filter(
        staff=staff,
        payroll_run__month=month,
        payroll_run__year=year,
    ).select_related('payroll_run').prefetch_related('allowance_lines').first()

    allowances = staff.get_active_allowances()
    projected_base = staff.base_salary
    projected_allowances = staff.get_monthly_allowances_total()
    projected_net = staff.get_projected_monthly_pay()

    payment_history = staff.salary_payments.all()[:20]
    past_payrolls = staff.payroll_items.select_related('payroll_run').order_by(
        '-payroll_run__year', '-payroll_run__month'
    )[:12]

    ytd_paid = staff.salary_payments.filter(
        payment_date__year=year
    ).aggregate(total=Sum('amount_paid'))['total'] or 0

    return render(request, 'staff/my_payroll.html', {
        'staff': staff,
        'current_item': current_item,
        'allowances': allowances,
        'projected_base': projected_base,
        'projected_allowances': projected_allowances,
        'projected_net': projected_net,
        'payment_history': payment_history,
        'past_payrolls': past_payrolls,
        'ytd_paid': ytd_paid,
        'current_month': month,
        'current_year': year,
    })