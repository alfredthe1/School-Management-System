from django import forms
from students.models import Student
from fees.models import FeeStructure
from core.models import AcademicYear


class LinkChildForm(forms.Form):
    student_id = forms.CharField(
        max_length=20,
        label='Student ID',
        widget=forms.TextInput(attrs={'placeholder': 'HCN/2026/001', 'class': 'form-control'})
    )
    date_of_birth = forms.DateField(
        label='Child date of birth',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    def clean(self):
        cleaned = super().clean()
        student_id = cleaned.get('student_id', '').strip()
        dob = cleaned.get('date_of_birth')
        if student_id and dob:
            try:
                student = Student.objects.get(student_id__iexact=student_id, date_of_birth=dob, is_active=True)
            except Student.DoesNotExist:
                raise forms.ValidationError('No active student found with that ID and date of birth.')
            if student.parent:
                raise forms.ValidationError('This child is already linked to a parent account.')
            cleaned['student'] = student
        return cleaned


class ParentMobileMoneyPaymentForm(forms.Form):
    PROVIDER_CHOICES = [
        ('mtn', 'MTN Mobile Money'),
        ('airtel', 'Airtel Money'),
    ]
    provider = forms.ChoiceField(
        choices=PROVIDER_CHOICES,
        label='Mobile money network',
        widget=forms.RadioSelect(attrs={'class': 'provider-radio'}),
    )
    fee_structure = forms.ModelChoiceField(
        queryset=FeeStructure.objects.none(),
        label='Fee item',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    amount = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    phone_number = forms.CharField(
        max_length=15,
        label='Mobile money number',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '07XX XXX XXX (MTN or Airtel)',
        }),
        help_text='Uganda number registered on MTN Mobile Money or Airtel Money.',
    )

    def __init__(self, *args, student=None, parent=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.student = student
        if student and student.current_class:
            current_year = AcademicYear.objects.filter(is_current=True).first()
            qs = FeeStructure.objects.filter(class_room=student.current_class)
            if current_year:
                qs = qs.filter(academic_year=current_year)
            self.fields['fee_structure'].queryset = qs
        if parent and parent.phone:
            self.fields['phone_number'].initial = parent.phone