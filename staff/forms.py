from django import forms
from django.contrib.auth import get_user_model

from .models import StaffAllowance, StaffMember, SalaryPayment, PayrollItem

User = get_user_model()

STAFF_ROLES = [
    ('admin', 'Admin'),
    ('headteacher', 'Head Teacher'),
    ('teacher', 'Teacher'),
    ('bursar', 'Bursar'),
]


class StaffMemberForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=False)
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        help_text='Leave blank to keep existing password.',
    )
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=False)
    role = forms.ChoiceField(choices=STAFF_ROLES, required=True)
    link_existing_user = forms.ModelChoiceField(
        queryset=User.objects.filter(
            role__in=['admin', 'headteacher', 'teacher', 'bursar'],
            staff_profile__isnull=True,
        ),
        required=False,
        label='Link existing user account',
        help_text='Optional — pick an existing account without a staff profile.',
    )

    class Meta:
        model = StaffMember
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender',
            'job_title', 'department', 'qualification', 'date_joined',
            'employment_type', 'base_salary',
            'phone', 'email', 'address',
            'bank_name', 'bank_account', 'profile_pic', 'is_active', 'notes',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'date_joined': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
            'base_salary': forms.NumberInput(attrs={'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.user:
            self.fields['username'].initial = self.instance.user.username
            self.fields['role'].initial = self.instance.user.role
            self.fields['link_existing_user'].widget = forms.HiddenInput()
        else:
            self.fields['username'].required = False

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        confirm = cleaned.get('confirm_password')
        if password and password != confirm:
            raise forms.ValidationError('Passwords do not match.')

        if not self.instance.pk:
            link_user = cleaned.get('link_existing_user')
            username = cleaned.get('username')
            if not link_user and not username:
                raise forms.ValidationError(
                    'Provide a username for a new account or select an existing user to link.'
                )
            if not link_user and not password:
                raise forms.ValidationError('Password is required for new user accounts.')
        return cleaned

    def save(self, commit=True):
        staff = super().save(commit=False)
        role = self.cleaned_data['role']

        if not self.instance.pk:
            link_user = self.cleaned_data.get('link_existing_user')
            if link_user:
                user = link_user
                user.role = role
            else:
                user = User.objects.create_user(
                    username=self.cleaned_data['username'],
                    password=self.cleaned_data['password'],
                    role=role,
                )
            user.first_name = self.cleaned_data.get('first_name', '')
            user.last_name = self.cleaned_data.get('last_name', '')
            user.email = self.cleaned_data.get('email', '')
            user.phone = self.cleaned_data.get('phone', '')
            user.address = self.cleaned_data.get('address', '')
            user.save()
            staff.user = user

            if role == 'teacher':
                from teachers.models import Teacher
                if not hasattr(user, 'teacher_profile'):
                    Teacher.objects.create(
                        user=user,
                        first_name=staff.first_name,
                        last_name=staff.last_name,
                        date_of_birth=staff.date_of_birth,
                        gender=staff.gender or '',
                        qualification=staff.qualification,
                        phone=staff.phone,
                        email=staff.email,
                        address=staff.address,
                        is_active=staff.is_active,
                    )
        else:
            user = staff.user
            user.first_name = self.cleaned_data.get('first_name', '')
            user.last_name = self.cleaned_data.get('last_name', '')
            user.email = self.cleaned_data.get('email', '')
            user.phone = self.cleaned_data.get('phone', '')
            user.address = self.cleaned_data.get('address', '')
            user.role = role
            password = self.cleaned_data.get('password')
            if password:
                user.set_password(password)
            user.save()

            if role == 'teacher' and hasattr(user, 'teacher_profile'):
                teacher = user.teacher_profile
                teacher.first_name = staff.first_name
                teacher.last_name = staff.last_name
                teacher.phone = staff.phone
                teacher.email = staff.email
                teacher.is_active = staff.is_active
                teacher.save()

        if commit:
            staff.save()
        return staff


class StaffAllowanceForm(forms.ModelForm):
    class Meta:
        model = StaffAllowance
        fields = ['name', 'amount', 'description', 'is_active']
        widgets = {
            'amount': forms.NumberInput(attrs={'step': '0.01'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }


class PayrollItemEditForm(forms.ModelForm):
    class Meta:
        model = PayrollItem
        fields = ['deductions', 'notes']
        widgets = {
            'deductions': forms.NumberInput(attrs={'step': '0.01'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class SalaryPaymentForm(forms.ModelForm):
    class Meta:
        model = SalaryPayment
        fields = [
            'amount_paid', 'payment_date', 'payment_method', 'reference', 'remarks',
        ]
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'amount_paid': forms.NumberInput(attrs={'step': '0.01'}),
            'remarks': forms.Textarea(attrs={'rows': 2}),
        }