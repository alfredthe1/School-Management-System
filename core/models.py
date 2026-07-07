from django.db import models
from django.conf import settings

class AcademicYear(models.Model):
    name = models.CharField(max_length=20, unique=True)  # "2025-2026"
    is_current = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_current:
            AcademicYear.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Term(models.Model):
    name = models.CharField(max_length=20)  # "First Term", "Second Term"
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        unique_together = ['name', 'academic_year']

    def __str__(self):
        return f"{self.name} ({self.academic_year})"

class ClassRoom(models.Model):
    name = models.CharField(max_length=50)   # "Nursery 1", "Primary 5"
    section = models.CharField(max_length=10, blank=True, verbose_name='Stream')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    class_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='classes_led',
        limit_choices_to={'role__in': ['teacher', 'headteacher']},
        verbose_name='Class teacher',
    )
    capacity = models.PositiveIntegerField(default=60)

    class Meta:
        unique_together = ['name', 'section', 'academic_year']
        ordering = ['academic_year__name', 'name', 'section']
        verbose_name = 'Class'
        verbose_name_plural = 'Classes'

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        base = self.name.strip()
        if self.section:
            return f'{base} — Stream {self.section}'
        return base

    @property
    def stream_label(self):
        return self.section.strip() if self.section else 'General'

    def student_count(self):
        from students.models import Student
        return Student.objects.filter(current_class=self, is_active=True).count()

class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    class_room = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name='subjects')
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role__in': ['teacher', 'headteacher']},
    )

    class Meta:
        unique_together = ['class_room', 'code']
        ordering = ['class_room__name', 'name']

    def __str__(self):
        return f"{self.name} ({self.code}) — {self.class_room}"
    
# core/models.py (events)

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    is_upcoming = models.BooleanField(default=True)
    image = models.ImageField(upload_to='events/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['date']

class SchoolDocument(models.Model):
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='documents/')
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=[
        ('policy', 'Policy'),
        ('form', 'Form'),
        ('report', 'Report'),
        ('other', 'Other')
    ])
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.title
    
class SchoolTheme(models.Model):
    primary_color = models.CharField(max_length=7, default='#4AA3DF')
    secondary_color = models.CharField(max_length=7, default='#2C7BB6')
    accent_color = models.CharField(max_length=7, default='#F4A460')
    font_family = models.CharField(max_length=100, default='Open Sans')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return "Current Theme"


class SchoolPortalSettings(models.Model):
    """Singleton school-wide parent portal configuration."""
    block_parent_results_on_fee_balance = models.BooleanField(
        default=False,
        verbose_name='Hide results when fees are outstanding',
        help_text=(
            'When enabled, parents cannot view exam results while their child '
            'has an outstanding fee balance.'
        ),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'school portal settings'
        verbose_name_plural = 'school portal settings'

    def __str__(self):
        state = 'on' if self.block_parent_results_on_fee_balance else 'off'
        return f'Parent portal settings (fee balance block: {state})'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class LandingImage(models.Model):
    """Images uploaded by admin/headteacher for the public landing page gallery/hero."""
    title = models.CharField(max_length=100, blank=True)
    image = models.ImageField(upload_to='landing/')
    caption = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-uploaded_at']

    def __str__(self):
        return self.title or f"Landing Image {self.id}"


class LessonPlan(models.Model):
    """Teacher lesson plans."""
    teacher = models.ForeignKey('teachers.Teacher', on_delete=models.CASCADE, related_name='lesson_plans')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    class_room = models.ForeignKey(ClassRoom, on_delete=models.CASCADE)
    date = models.DateField()
    topic = models.CharField(max_length=200)
    objectives = models.TextField()
    activities = models.TextField()
    resources = models.TextField(blank=True)
    assessment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.topic} - {self.class_room}"