from django import forms
from django.contrib.auth import get_user_model
from .models import Teacher
from core.models import Subject

User = get_user_model()

class TeacherForm(forms.ModelForm):
    # User fields (to create the user account)
    username = forms.CharField(max_length=150, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=False, help_text="Leave blank to keep existing password")
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=False)

    class Meta:
        model = Teacher
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender',
            'qualification', 'subjects_taught',
            'phone', 'email', 'address', 'profile_pic', 'is_active'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'date_of_birth': 'Date of Birth',
            'subjects_taught': 'Subjects Taught',
            'is_active': 'Active Status',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subjects_taught'].queryset = Subject.objects.all().order_by('name')
        self.fields['subjects_taught'].widget = forms.SelectMultiple(attrs={'class': 'form-select'})

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm = cleaned_data.get('confirm_password')
        if password and password != confirm:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        teacher = super().save(commit=False)
        user = None

        # Check if we're creating a new teacher or updating an existing one
        if not self.instance.pk:
            # Create new user
            username = self.cleaned_data['username']
            password = self.cleaned_data['password']
            if not password:
                # Generate a random password if not provided
                password = User.objects.make_random_password()
            user = User.objects.create_user(
                username=username,
                password=password,
                role='teacher'
            )
            # Update user with teacher's name
            user.first_name = self.cleaned_data.get('first_name', '')
            user.last_name = self.cleaned_data.get('last_name', '')
            user.email = self.cleaned_data.get('email', '')
            user.phone = self.cleaned_data.get('phone', '')
            user.address = self.cleaned_data.get('address', '')
            user.save()
            teacher.user = user
        else:
            # Update existing teacher's user info
            user = teacher.user
            user.first_name = self.cleaned_data.get('first_name', '')
            user.last_name = self.cleaned_data.get('last_name', '')
            user.email = self.cleaned_data.get('email', '')
            user.phone = self.cleaned_data.get('phone', '')
            user.address = self.cleaned_data.get('address', '')
            # Handle password change
            password = self.cleaned_data.get('password')
            if password:
                user.set_password(password)
            user.save()

        if commit:
            teacher.save()
            self.save_m2m()
        return teacher