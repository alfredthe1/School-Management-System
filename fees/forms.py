from django import forms
from .models import FeeStructure, Payment, Expenditure


class ParentResultsPolicyForm(forms.Form):
    block_parent_results_on_fee_balance = forms.BooleanField(
        required=False,
        label='Hide results from parents with outstanding fee balances',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )



from core.models import AcademicYear, ClassRoom

class FeeStructureForm(forms.ModelForm):
    class Meta:
        model = FeeStructure
        fields = ['name', 'amount', 'academic_year', 'class_room']
        widgets = {
            'amount': forms.NumberInput(attrs={'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['academic_year'].queryset = AcademicYear.objects.all()
        self.fields['class_room'].queryset = ClassRoom.objects.all().order_by('name')


class ExpenditureForm(forms.ModelForm):
    class Meta:
        model = Expenditure
        fields = ['description', 'amount', 'category', 'receipt']
        widgets = {
            'amount': forms.NumberInput(attrs={'step': '0.01'}),
            'description': forms.Textarea(attrs={'rows': 2}),
        }


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['fee_structure', 'amount_paid', 'payment_method', 'remarks']
        widgets = {
            'amount_paid': forms.NumberInput(attrs={'step': '0.01'}),
            'remarks': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fee_structure'].queryset = FeeStructure.objects.all()
        self.fields['fee_structure'].required = False


class RecordPaymentForm(forms.ModelForm):
    """Record a payment with student selection (for bursar/admin)."""
    student = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Search by typing in the dropdown (browser search) or use student ID.',
    )

    class Meta:
        model = Payment
        fields = ['student', 'fee_structure', 'amount_paid', 'payment_method', 'remarks']
        widgets = {
            'amount_paid': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'fee_structure': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        from students.models import Student
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = Student.objects.filter(
            is_active=True
        ).select_related('current_class').order_by('last_name', 'first_name')
        self.fields['fee_structure'].queryset = FeeStructure.objects.all()
        self.fields['fee_structure'].required = False
        self.fields['student'].label_from_instance = (
            lambda s: f'{s.student_id} — {s.get_full_name()} ({s.current_class or "No class"})'
        )