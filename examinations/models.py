from django.db import models
from django.conf import settings
from core.models import Subject, Term, ClassRoom
from students.models import Student
from teachers.models import Teacher

class Exam(models.Model):
    name = models.CharField(max_length=100)  # e.g., "Mid-Term", "Final"
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    class_room = models.ForeignKey(ClassRoom, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    max_marks = models.PositiveIntegerField(default=100)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} – {self.subject.name} ({self.class_room})"

    class Meta:
        ordering = ['-start_date']


class ExamResult(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    grade = models.CharField(max_length=2, blank=True)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"{self.student} – {self.exam.subject} : {self.marks_obtained}"

    def save(self, *args, **kwargs):
        # Auto-assign grade based on a scale (you can customise)
        from .models import GradeScale
        scale = GradeScale.objects.filter(
            min_score__lte=self.marks_obtained,
            max_score__gte=self.marks_obtained
        ).first()
        self.grade = scale.grade if scale else 'F'
        super().save(*args, **kwargs)


class GradeScale(models.Model):
    name = models.CharField(max_length=50)
    min_score = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=2)
    remark = models.CharField(max_length=100)

    class Meta:
        ordering = ['-min_score']

    def __str__(self):
        return f"{self.grade}: {self.min_score} – {self.max_score}"