from django import forms
from django.contrib.auth import get_user_model
from .models import AcademicYear, ClassRoom, LandingImage, LessonPlan, Subject
from core.helpers import get_current_academic_year

User = get_user_model()


class ClassRoomForm(forms.ModelForm):
    class Meta:
        model = ClassRoom
        fields = ['name', 'section', 'academic_year', 'class_teacher', 'capacity']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Primary 5'}),
            'section': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. A, B, East'}),
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'class_teacher': forms.Select(attrs={'class': 'form-select'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }
        labels = {
            'section': 'Stream',
            'class_teacher': 'Class Teacher',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['academic_year'].queryset = AcademicYear.objects.order_by('-name')
        self.fields['class_teacher'].queryset = User.objects.filter(
            role__in=['teacher', 'headteacher'], is_active=True
        ).order_by('first_name', 'last_name')
        self.fields['class_teacher'].required = False
        if not self.instance.pk and not self.initial.get('academic_year'):
            current = get_current_academic_year()
            if current:
                self.fields['academic_year'].initial = current.pk


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'code', 'class_room', 'teacher']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Mathematics'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. MATH-P5'}),
            'class_room': forms.Select(attrs={'class': 'form-select'}),
            'teacher': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        year = get_current_academic_year()
        qs = ClassRoom.objects.select_related('academic_year').order_by('name', 'section')
        if year:
            qs = qs.filter(academic_year=year)
        self.fields['class_room'].queryset = qs
        self.fields['class_room'].label_from_instance = lambda obj: obj.display_name
        self.fields['teacher'].queryset = User.objects.filter(
            role__in=['teacher', 'headteacher'], is_active=True
        ).order_by('first_name', 'last_name')
        self.fields['teacher'].required = False


class SubjectAssignmentForm(forms.Form):
    """Dynamic teacher pickers per subject in a class."""

    def __init__(self, *args, classroom=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.classroom = classroom
        if not classroom:
            return
        teachers = User.objects.filter(role__in=['teacher', 'headteacher'], is_active=True).order_by(
            'first_name', 'last_name'
        )
        for subject in classroom.subjects.order_by('name'):
            self.fields[f'teacher_{subject.id}'] = forms.ModelChoiceField(
                queryset=teachers,
                required=False,
                label=subject.name,
                initial=subject.teacher_id,
                widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
            )

class LandingImageForm(forms.ModelForm):
    class Meta:
        model = LandingImage
        fields = ['title', 'image', 'caption', 'order', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'caption': forms.TextInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class LessonPlanForm(forms.ModelForm):
    class Meta:
        model = LessonPlan
        fields = ['subject', 'class_room', 'date', 'topic', 'objectives', 'activities', 'resources', 'assessment']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'topic': forms.TextInput(attrs={'class': 'form-control'}),
            'objectives': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'activities': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'resources': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'assessment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }