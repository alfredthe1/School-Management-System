from django.contrib import admin
from .models import Exam, GradeScale, ExamResult

admin.site.register(Exam)
admin.site.register(GradeScale)
admin.site.register(ExamResult)