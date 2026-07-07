from django.db import models
from django.conf import settings
from django.utils import timezone
from core.models import Subject

class Teacher(models.Model):
    # User link (authentication)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_profile'
    )

    # Personal details
    first_name = models.CharField(max_length=50, default='')
    last_name = models.CharField(max_length=50, default='')
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female')], blank=True)

    # Employment details
    employee_id = models.CharField(max_length=20, unique=True, blank=True, editable=False)
    qualification = models.CharField(max_length=200, blank=True)
    date_joined = models.DateField(auto_now_add=True)

    # Subjects taught
    subjects_taught = models.ManyToManyField(Subject, blank=True, related_name='teachers_teaching')

    # Contact
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    # Photo
    profile_pic = models.ImageField(upload_to='teacher_photos/', blank=True, null=True)

    # Status
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.get_full_name()} ({self.employee_id})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def save(self, *args, **kwargs):
        if not self.employee_id:
            year = timezone.now().strftime('%Y')
            last_teacher = Teacher.objects.filter(
                employee_id__startswith=f'TCH/{year}/'
            ).order_by('employee_id').last()

            if last_teacher:
                last_number = int(last_teacher.employee_id.split('/')[-1])
                new_number = last_number + 1
            else:
                new_number = 1

            self.employee_id = f'TCH/{year}/{new_number:03d}'

        super().save(*args, **kwargs)

    class Meta:
        ordering = ['last_name', 'first_name']