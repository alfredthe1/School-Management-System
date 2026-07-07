"""Admin portal: classes, streams, subjects, and teacher assignments."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from core.forms import ClassRoomForm, SubjectAssignmentForm, SubjectForm
from core.helpers import classrooms_queryset, get_current_academic_year, structure_manager_check
from core.models import AcademicYear, ClassRoom, Subject
from students.models import Student
from teachers.models import Teacher

User = get_user_model()


@login_required
@user_passes_test(structure_manager_check)
def class_list(request):
    year_id = request.GET.get('year')
    years = AcademicYear.objects.order_by('-name')
    year = None
    if year_id:
        year = years.filter(pk=year_id).first()
    if not year:
        year = get_current_academic_year()

    classes = classrooms_queryset(year)
    search = request.GET.get('search', '').strip()
    if search:
        classes = classes.filter(
            Q(name__icontains=search) | Q(section__icontains=search)
        )

    class_rows = []
    for classroom in classes:
        class_rows.append({
            'classroom': classroom,
            'student_count': classroom.student_count(),
            'subject_count': classroom.subjects.count(),
        })

    return render(request, 'core/classes/class_list.html', {
        'class_rows': class_rows,
        'years': years,
        'selected_year': year,
        'search': search,
    })


@login_required
@user_passes_test(structure_manager_check)
def class_detail(request, pk):
    classroom = get_object_or_404(
        ClassRoom.objects.select_related('academic_year', 'class_teacher'),
        pk=pk,
    )
    subjects = classroom.subjects.select_related('teacher').order_by('name')
    students = Student.objects.filter(current_class=classroom, is_active=True).order_by('first_name')
    return render(request, 'core/classes/class_detail.html', {
        'classroom': classroom,
        'subjects': subjects,
        'students': students,
    })


@login_required
@user_passes_test(structure_manager_check)
def class_create(request):
    if request.method == 'POST':
        form = ClassRoomForm(request.POST)
        if form.is_valid():
            classroom = form.save()
            messages.success(request, f'Class {classroom.display_name} created.')
            return redirect('core:class_detail', pk=classroom.pk)
    else:
        form = ClassRoomForm()
    return render(request, 'core/classes/class_form.html', {
        'form': form,
        'title': 'Add Class & Stream',
    })


@login_required
@user_passes_test(structure_manager_check)
def class_edit(request, pk):
    classroom = get_object_or_404(ClassRoom, pk=pk)
    if request.method == 'POST':
        form = ClassRoomForm(request.POST, instance=classroom)
        if form.is_valid():
            form.save()
            messages.success(request, 'Class updated successfully.')
            return redirect('core:class_detail', pk=classroom.pk)
    else:
        form = ClassRoomForm(instance=classroom)
    return render(request, 'core/classes/class_form.html', {
        'form': form,
        'title': f'Edit {classroom.display_name}',
        'classroom': classroom,
    })


@login_required
@user_passes_test(structure_manager_check)
def class_delete(request, pk):
    classroom = get_object_or_404(ClassRoom, pk=pk)
    if request.method == 'POST':
        name = classroom.display_name
        classroom.delete()
        messages.success(request, f'{name} deleted.')
        return redirect('core:class_list')
    return render(request, 'core/classes/class_confirm_delete.html', {'classroom': classroom})


@login_required
@user_passes_test(structure_manager_check)
def subject_list(request):
    year_id = request.GET.get('year')
    class_id = request.GET.get('class')
    years = AcademicYear.objects.order_by('-name')
    year = years.filter(pk=year_id).first() if year_id else get_current_academic_year()

    subjects = Subject.objects.select_related('class_room', 'class_room__academic_year', 'teacher')
    if year:
        subjects = subjects.filter(class_room__academic_year=year)
    if class_id:
        subjects = subjects.filter(class_room_id=class_id)

    classes = classrooms_queryset(year)
    search = request.GET.get('search', '').strip()
    if search:
        subjects = subjects.filter(
            Q(name__icontains=search) | Q(code__icontains=search) | Q(class_room__name__icontains=search)
        )

    return render(request, 'core/subjects/subject_list.html', {
        'subjects': subjects.order_by('class_room__name', 'name'),
        'years': years,
        'classes': classes,
        'selected_year': year,
        'selected_class_id': class_id,
        'search': search,
    })


@login_required
@user_passes_test(structure_manager_check)
def subject_create(request):
    class_id = request.GET.get('class')
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save()
            _sync_teacher_subjects(subject)
            messages.success(request, f'Subject {subject.name} added.')
            return redirect('core:class_detail', pk=subject.class_room_id)
    else:
        initial = {}
        if class_id:
            initial['class_room'] = class_id
        form = SubjectForm(initial=initial)
    return render(request, 'core/subjects/subject_form.html', {
        'form': form,
        'title': 'Add Subject',
    })


@login_required
@user_passes_test(structure_manager_check)
def subject_edit(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    if request.method == 'POST':
        form = SubjectForm(request.POST, instance=subject)
        if form.is_valid():
            subject = form.save()
            _sync_teacher_subjects(subject)
            messages.success(request, 'Subject updated.')
            return redirect('core:class_detail', pk=subject.class_room_id)
    else:
        form = SubjectForm(instance=subject)
    return render(request, 'core/subjects/subject_form.html', {
        'form': form,
        'title': f'Edit {subject.name}',
        'subject': subject,
    })


@login_required
@user_passes_test(structure_manager_check)
def subject_delete(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    class_pk = subject.class_room_id
    if request.method == 'POST':
        subject.delete()
        messages.success(request, 'Subject removed.')
        return redirect('core:class_detail', pk=class_pk)
    return render(request, 'core/subjects/subject_confirm_delete.html', {'subject': subject})


@login_required
@user_passes_test(structure_manager_check)
def subject_assignments(request):
    year = get_current_academic_year()
    class_id = request.GET.get('class') or request.POST.get('class_room')
    classroom = None
    subjects = Subject.objects.none()

    if class_id:
        classroom = get_object_or_404(ClassRoom, pk=class_id)
        subjects = classroom.subjects.select_related('teacher').order_by('name')

    if request.method == 'POST' and classroom:
        form = SubjectAssignmentForm(request.POST, classroom=classroom)
        if form.is_valid():
            updated = 0
            for subject in subjects:
                field = f'teacher_{subject.id}'
                teacher = form.cleaned_data.get(field)
                if teacher:
                    if subject.teacher_id != teacher.id:
                        subject.teacher = teacher
                        subject.save()
                        _sync_teacher_subjects(subject)
                        updated += 1
                elif subject.teacher_id:
                    subject.teacher = None
                    subject.save()
                    updated += 1
            messages.success(request, f'Teacher assignments updated ({updated} changes).')
            return redirect(f'{request.path}?class={classroom.pk}')
    else:
        form = SubjectAssignmentForm(classroom=classroom) if classroom else None

    classes = classrooms_queryset(year)
    unassigned = Subject.objects.filter(class_room__academic_year=year, teacher__isnull=True).count() if year else 0

    return render(request, 'core/subjects/subject_assignments.html', {
        'form': form,
        'classroom': classroom,
        'subjects': subjects,
        'classes': classes,
        'selected_year': year,
        'unassigned_count': unassigned,
    })


def _sync_teacher_subjects(subject):
    """Keep Teacher.subjects_taught in sync with Subject.teacher."""
    if not subject.teacher_id:
        return
    try:
        teacher_profile = Teacher.objects.get(user_id=subject.teacher_id)
        teacher_profile.subjects_taught.add(subject)
    except Teacher.DoesNotExist:
        pass