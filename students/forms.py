from django import forms
from django.contrib.auth import get_user_model
from .models import Student
from core.models import ClassRoom, Subject, Term
from core.helpers import get_current_academic_year
from academics.models import StudentResult

User = get_user_model()

class StudentForm(forms.ModelForm):
    new_parent_name = forms.CharField(
        max_length=100,
        required=False,
        label="Or add a new parent (Full Name)",
        help_text="Leave blank to select from the dropdown below."
    )

    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender',
            'current_class', 'parent', 'emergency_contact',
            'address', 'profile_pic', 'is_active'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'date_of_birth': 'Date of Birth',
            'current_class': 'Class',
            'emergency_contact': 'Emergency Contact',
            'profile_pic': 'Profile Photo',
            'is_active': 'Active Status',
            'parent': 'Select existing parent',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parent'].queryset = User.objects.filter(role='parent').order_by('username')
        self.fields['parent'].label_from_instance = lambda obj: f"{obj.get_full_name()} ({obj.username})"
        year = get_current_academic_year()
        class_qs = ClassRoom.objects.select_related('academic_year').order_by('name', 'section')
        if year:
            class_qs = class_qs.filter(academic_year=year)
        self.fields['current_class'].queryset = class_qs
        self.fields['current_class'].label_from_instance = lambda obj: obj.display_name

    def save(self, commit=True):
        student = super().save(commit=False)
        new_parent_name = self.cleaned_data.get('new_parent_name')
        if new_parent_name:
            # Split into first and last name
            parts = new_parent_name.strip().split(' ', 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ''
            # Generate a unique username
            base_username = new_parent_name.lower().replace(' ', '_')
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            # Create the parent user (password will be set later)
            parent_user = User.objects.create_user(
                username=username,
                password=User.objects.make_random_password(),
                first_name=first_name,
                last_name=last_name,
                role='parent'
            )
            student.parent = parent_user
        if commit:
            student.save()
        return student


class StudentResultForm(forms.ModelForm):
    class Meta:
        model = StudentResult
        fields = ['subject', 'term', 'test_score', 'exam_score', 'grade']
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'term': forms.Select(attrs={'class': 'form-select'}),
            'test_score': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'exam_score': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'grade': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 2}),
        }

    def __init__(self, *args, student=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.role == 'teacher':
            try:
                subjects = user.teacher_profile.subjects_taught.all()
                if student and student.current_class_id:
                    subjects = subjects.filter(class_room=student.current_class)
                self.fields['subject'].queryset = subjects.order_by('name')
            except Exception:
                self.fields['subject'].queryset = Subject.objects.none()
        else:
            if student and student.current_class:
                self.fields['subject'].queryset = Subject.objects.filter(
                    class_room=student.current_class
                ).order_by('name')
            else:
                self.fields['subject'].queryset = Subject.objects.all().order_by('name')
        self.fields['term'].queryset = Term.objects.select_related('academic_year').order_by('-academic_year__name')