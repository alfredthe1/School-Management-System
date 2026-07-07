"""Teacher-scoped subject and marks helpers."""
from django.db.models import Avg, Count

from core.models import Subject


def get_teacher_profile(user):
    if user.role != 'teacher':
        return None
    try:
        return user.teacher_profile
    except Exception:
        return None


def get_teacher_subjects(user, class_room=None):
    """Subjects assigned to this teacher (optional filter by class)."""
    teacher = get_teacher_profile(user)
    if not teacher:
        return Subject.objects.none()
    qs = teacher.subjects_taught.select_related('class_room').order_by(
        'class_room__name', 'name'
    )
    if class_room is not None:
        qs = qs.filter(class_room=class_room)
    return qs


def get_teacher_subject_ids(user, class_room=None):
    return list(get_teacher_subjects(user, class_room=class_room).values_list('id', flat=True))


def teacher_teaches_subject(user, subject):
    if user.role in ('admin', 'headteacher'):
        return True
    if user.role != 'teacher' or subject is None:
        return False
    return get_teacher_subjects(user).filter(pk=subject.pk).exists()


def teacher_can_edit_exam(user, exam):
    """Teacher may edit marks only for exams in their assigned subject(s)."""
    if user.role in ('admin', 'headteacher'):
        return True
    if user.role != 'teacher':
        return False
    return get_teacher_subjects(user).filter(pk=exam.subject_id).exists()


def teacher_subject_assignments(user):
    """Grouped subject-class rows for teacher dashboard."""
    assignments = []
    for subject in get_teacher_subjects(user):
        assignments.append({
            'subject': subject,
            'class_room': subject.class_room,
            'label': f'{subject.name} — {subject.class_room}',
        })
    return assignments


def exam_marking_stats(exam):
    """How many students in the class have marks for this exam."""
    from examinations.models import ExamResult
    from students.models import Student

    class_size = Student.objects.filter(
        current_class=exam.class_room, is_active=True
    ).count()
    marked = ExamResult.objects.filter(
        exam=exam, marks_obtained__isnull=False
    ).exclude(marks_obtained=0).count()
    # Also count any result row with marks entered (including 0)
    entered = ExamResult.objects.filter(exam=exam).count()
    avg = ExamResult.objects.filter(exam=exam).aggregate(avg=Avg('marks_obtained'))['avg']
    return {
        'class_size': class_size,
        'entered': entered,
        'marked': marked,
        'avg': round(float(avg), 1) if avg is not None else None,
        'complete': class_size > 0 and entered >= class_size,
    }