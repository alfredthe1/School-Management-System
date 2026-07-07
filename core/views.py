import json
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.db.models import Sum
from .models import Event, LandingImage, LessonPlan, ClassRoom, AcademicYear
from .forms import LandingImageForm, LessonPlanForm
from .helpers import (
    get_fee_collection_chart_data,
    get_class_performance_chart_data,
    get_recent_payments,
)
from students.models import Student
from teachers.models import Teacher
from fees.models import Payment, Expenditure, FeeStructure
from examinations.models import Exam


def home(request):
    upcoming_events = Event.objects.filter(is_upcoming=True)[:5]
    landing_images = LandingImage.objects.filter(is_active=True)[:6]
    return render(request, 'core/home.html', {
        'upcoming_events': upcoming_events,
        'landing_images': landing_images
    })


@method_decorator(login_required, name='dispatch')
class DashboardView(TemplateView):
    template_name = 'core/dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == 'parent':
            return redirect('parents:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        current_year = AcademicYear.objects.filter(is_current=True).first()
        context['current_year'] = current_year

        if user.role in ['admin', 'headteacher']:
            context['total_students'] = Student.objects.filter(is_active=True).count()
            context['total_teachers'] = Teacher.objects.filter(is_active=True).count()
            total_collected = Payment.objects.aggregate(total=Sum('amount_paid'))['total'] or 0
            context['total_collected'] = total_collected
            total_due = 0
            if current_year:
                per_student = FeeStructure.objects.filter(academic_year=current_year).aggregate(
                    total=Sum('amount')
                )['total'] or 0
                total_due = per_student * Student.objects.filter(is_active=True).count()
            context['pending_fees'] = max(total_due - total_collected, 0)
            context['recent_payments'] = get_recent_payments(8)

            fee_labels, fee_values = get_fee_collection_chart_data()
            perf_labels, perf_values = get_class_performance_chart_data()
            context['fee_chart_labels'] = json.dumps(fee_labels)
            context['fee_chart_values'] = json.dumps(fee_values)
            context['perf_chart_labels'] = json.dumps(perf_labels)
            context['perf_chart_values'] = json.dumps(perf_values)

        if user.role == 'bursar':
            today = timezone.now().date()
            collections = Payment.objects.filter(date_paid=today).aggregate(
                total=Sum('amount_paid')
            )['total'] or 0
            context['todays_collections'] = collections
            context['recent_payments'] = get_recent_payments(15)
            total_collected = Payment.objects.aggregate(total=Sum('amount_paid'))['total'] or 0
            context['total_collected'] = total_collected
            context['pending_fees'] = 0

        if user.role == 'teacher':
            try:
                teacher = user.teacher_profile
                subjects = teacher.subjects_taught.all()
                context['subjects'] = subjects

                subject_students = {}
                for subject in subjects:
                    students = Student.objects.filter(
                        current_class=subject.class_room, is_active=True
                    ).order_by('last_name', 'first_name')
                    subject_students[subject.name] = students
                context['subject_students'] = subject_students

                exams = Exam.objects.filter(
                    subject__in=subjects, start_date__gte=timezone.now().date()
                ).order_by('start_date')
                context['upcoming_exams'] = exams
                context['total_students_teacher'] = Student.objects.filter(
                    current_class__in=[s.class_room for s in subjects], is_active=True
                ).count()
                context['lesson_plans'] = LessonPlan.objects.filter(teacher=teacher)[:3]
            except Teacher.DoesNotExist:
                context['subjects'] = []
                context['subject_students'] = {}
                context['upcoming_exams'] = []
                context['total_students_teacher'] = 0
                context['lesson_plans'] = []

        context['upcoming_events'] = Event.objects.filter(is_upcoming=True)[:5]
        return context


@login_required
@user_passes_test(lambda u: u.role in ['admin', 'headteacher'])
def landing_images_upload(request):
    if request.method == 'POST':
        form = LandingImageForm(request.POST, request.FILES)
        if form.is_valid():
            img = form.save(commit=False)
            img.uploaded_by = request.user
            img.save()
            messages.success(request, "Image uploaded successfully to landing page.")
            return redirect('core:landing_images_upload')
    else:
        form = LandingImageForm()

    images = LandingImage.objects.all().order_by('order')
    return render(request, 'core/landing_images.html', {
        'form': form,
        'images': images
    })


@login_required
@user_passes_test(lambda u: u.role in ['admin', 'headteacher'])
def delete_landing_image(request, pk):
    if request.method == 'POST':
        try:
            img = LandingImage.objects.get(pk=pk)
            img.image.delete(save=False)
            img.delete()
            messages.success(request, "Image removed from landing page.")
        except LandingImage.DoesNotExist:
            pass
    return redirect('core:landing_images_upload')


@login_required
def teacher_lesson_plans(request):
    if request.user.role != 'teacher':
        messages.error(request, "Access restricted to teachers.")
        return redirect('core:dashboard')

    try:
        teacher = request.user.teacher_profile
    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect('core:dashboard')

    plans = LessonPlan.objects.filter(teacher=teacher).select_related('subject', 'class_room')[:15]

    if request.method == 'POST':
        form = LessonPlanForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.teacher = teacher
            plan.save()
            messages.success(request, "Lesson plan saved successfully!")
            return redirect('core:teacher_lesson_plans')
    else:
        form = LessonPlanForm()
        form.fields['subject'].queryset = teacher.subjects_taught.all()
        form.fields['class_room'].queryset = ClassRoom.objects.filter(
            subjects__in=teacher.subjects_taught.all()
        ).distinct()

    return render(request, 'teachers/lesson_plans.html', {
        'plans': plans,
        'form': form,
        'teacher': teacher
    })