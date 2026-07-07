from django import forms
from .models import LessonNote
from core.models import ClassRoom, Subject
from teachers.models import Teacher


class LessonNoteForm(forms.ModelForm):
    class Meta:
        model = LessonNote
        fields = ['teacher', 'subject', 'class_room', 'date', 'topic', 'content', 'attachments']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'topic': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'teacher': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'class_room': forms.Select(attrs={'class': 'form-select'}),
            'attachments': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        is_staff = user and user.role in ['admin', 'headteacher']

        if is_staff:
            self.fields['teacher'].queryset = Teacher.objects.filter(is_active=True).order_by(
                'last_name', 'first_name'
            )
            self.fields['subject'].queryset = Subject.objects.select_related('class_room').order_by('name')
            self.fields['class_room'].queryset = ClassRoom.objects.order_by('name')
        else:
            self.fields.pop('teacher', None)
            try:
                teacher = user.teacher_profile
                subjects = teacher.subjects_taught.all()
                self.fields['subject'].queryset = subjects
                self.fields['class_room'].queryset = ClassRoom.objects.filter(
                    subjects__in=subjects
                ).distinct().order_by('name')
            except Teacher.DoesNotExist:
                self.fields['subject'].queryset = Subject.objects.none()
                self.fields['class_room'].queryset = ClassRoom.objects.none()

    def clean(self):
        cleaned = super().clean()
        user = self.user
        if user and user.role == 'teacher':
            try:
                teacher = user.teacher_profile
            except Teacher.DoesNotExist:
                raise forms.ValidationError('Your account is not linked to a teacher profile.')
            subject = cleaned.get('subject')
            if subject and subject not in teacher.subjects_taught.all():
                raise forms.ValidationError('You can only create notes for your assigned subjects.')
            cleaned['teacher'] = teacher
        return cleaned