from django.db import models
from django.conf import settings
from django.utils import timezone
from core.models import ClassRoom

class Student(models.Model):
    # Personal details
    first_name = models.CharField(max_length=50, default='')
    last_name = models.CharField(max_length=50, default='')
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female')])
    student_id = models.CharField(max_length=20, unique=True, blank=True, editable=False)
    enrollment_date = models.DateField(auto_now_add=True)

    # Academic
    current_class = models.ForeignKey(ClassRoom, on_delete=models.SET_NULL, null=True)

    # Parent/Guardian
    parent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'parent'},
        related_name='children'
    )

    # Contact
    emergency_contact = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)

    # Photo
    profile_pic = models.ImageField(upload_to='student_photos/', blank=True, null=True)

    # Status
    is_active = models.BooleanField(default=True)

    PARENT_RESULTS_ACCESS_CHOICES = (
        ('default', 'Follow school policy'),
        ('allow', 'Always allow results'),
        ('block', 'Always block results'),
    )
    parent_results_access = models.CharField(
        max_length=10,
        choices=PARENT_RESULTS_ACCESS_CHOICES,
        default='default',
        help_text='Override whether this student\'s parent can view results on the portal.',
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.student_id})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def save(self, *args, **kwargs):
        if not self.student_id:
            year = timezone.now().strftime('%Y')
            last_student = Student.objects.filter(
                student_id__startswith=f'HCN/{year}/'
            ).order_by('student_id').last()
            
            if last_student:
                last_number = int(last_student.student_id.split('/')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.student_id = f'HCN/{year}/{new_number:03d}'
        
        super().save(*args, **kwargs)

    # Fee helper methods
    def get_total_fees_due(self):
        from fees.models import FeeStructure
        from core.models import AcademicYear
        if self.current_class:
            current_year = AcademicYear.objects.filter(is_current=True).first()
            if current_year:
                total = FeeStructure.objects.filter(
                    class_room=self.current_class,
                    academic_year=current_year
                ).aggregate(total=models.Sum('amount'))['total'] or 0
                return total
        return 0

    def get_total_fees_paid(self):
        from fees.models import Payment
        total = Payment.objects.filter(student=self).aggregate(total=models.Sum('amount_paid'))['total'] or 0
        return total

    def get_fees_balance(self):
        return self.get_total_fees_due() - self.get_total_fees_paid()

    class Meta:
        ordering = ['last_name', 'first_name']