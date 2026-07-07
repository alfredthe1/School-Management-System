"""Shared helpers for role-based access and dashboard analytics."""
from datetime import timedelta
from django.db.models import Sum, Avg
from django.db.models.functions import TruncMonth
from django.utils import timezone


def structure_manager_check(user):
    from accounts.permission_utils import user_can_access
    return user.is_authenticated and user_can_access(user, 'school_structure')


def get_current_academic_year():
    from core.models import AcademicYear
    return AcademicYear.objects.filter(is_current=True).first()


def classrooms_queryset(year=None):
    from core.models import ClassRoom
    qs = ClassRoom.objects.select_related('academic_year', 'class_teacher').order_by(
        'academic_year__name', 'name', 'section'
    )
    if year:
        qs = qs.filter(academic_year=year)
    return qs


def get_teacher_class_ids(user):
    """Return class IDs for classes the teacher teaches."""
    if user.role != 'teacher':
        return []
    try:
        return list(
            user.teacher_profile.subjects_taught.values_list('class_room_id', flat=True).distinct()
        )
    except Exception:
        return []


def get_teacher_subject_ids(user, class_room=None):
    from examinations.teacher_utils import get_teacher_subject_ids as _ids
    return _ids(user, class_room=class_room)


def teacher_teaches_student(user, student):
    if user.role != 'teacher':
        return True
    if not student.current_class_id:
        return False
    return student.current_class_id in get_teacher_class_ids(user)


def get_fee_collection_chart_data(months=6):
    """Monthly fee collections for the last N months."""
    from fees.models import Payment

    start = timezone.now().date().replace(day=1) - timedelta(days=months * 31)
    entries = (
        Payment.objects.filter(date_paid__gte=start)
        .annotate(month=TruncMonth('date_paid'))
        .values('month')
        .annotate(total=Sum('amount_paid'))
        .order_by('month')
    )
    labels, values = [], []
    for entry in entries:
        if entry['month']:
            labels.append(entry['month'].strftime('%b %Y'))
            values.append(float(entry['total'] or 0))
    return labels, values


def get_class_performance_chart_data():
    """Average exam score per class."""
    from core.models import ClassRoom
    from examinations.models import ExamResult

    labels, values = [], []
    for classroom in ClassRoom.objects.all().order_by('name'):
        avg = ExamResult.objects.filter(exam__class_room=classroom).aggregate(
            avg=Avg('marks_obtained')
        )['avg']
        if avg is not None:
            labels.append(str(classroom))
            values.append(round(float(avg), 1))
    return labels, values


def get_recent_payments(limit=8):
    from fees.models import Payment
    return Payment.objects.select_related('student', 'fee_structure').order_by('-date_paid')[:limit]