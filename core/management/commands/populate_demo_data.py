from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
import random

from accounts.models import User
from core.models import AcademicYear, Term, ClassRoom, Subject, Event, LessonPlan
from students.models import Student
from teachers.models import Teacher
from examinations.models import Exam, ExamResult, GradeScale
from academics.models import TimetableEntry, LessonNote, StudentResult, TimeSlot, TimeSlot
from fees.models import FeeStructure, Payment
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate demo data for Happy Child School'

    def handle(self, *args, **options):
        self.stdout.write("Creating demo data...")

        # Create Academic Year and Terms
        year, _ = AcademicYear.objects.get_or_create(name="2025-2026", defaults={'is_current': True})
        
        term1, _ = Term.objects.get_or_create(
            name="First Term", academic_year=year,
            defaults={'start_date': date(2025, 9, 1), 'end_date': date(2025, 12, 15), 'is_current': True}
        )
        term2, _ = Term.objects.get_or_create(
            name="Second Term", academic_year=year,
            defaults={'start_date': date(2026, 1, 10), 'end_date': date(2026, 4, 15), 'is_current': False}
        )

        # Create ClassRooms
        classes = []
        for i in range(1, 8):
            cls, _ = ClassRoom.objects.get_or_create(
                name=f"Primary {i}", academic_year=year, section=""
            )
            classes.append(cls)

        # Subjects per class (each class has its own subject records)
        subjects_data = [
            ("Mathematics", "MATH"),
            ("English", "ENG"),
            ("Science", "SCI"),
            ("Social Studies", "SOC"),
            ("Kiswahili", "KIS"),
        ]
        subjects_by_class = {}
        all_subjects = []
        for cls in classes[:5]:
            subjects_by_class[cls] = []
            class_num = cls.name.split()[-1]
            for name, code_base in subjects_data:
                subj, _ = Subject.objects.get_or_create(
                    class_room=cls,
                    code=f'{code_base}-P{class_num}',
                    defaults={'name': name},
                )
                subjects_by_class[cls].append(subj)
                all_subjects.append(subj)

        # Create GradeScale
        grades = [
            ("A", 80, 100, "Excellent"),
            ("B", 65, 79, "Very Good"),
            ("C", 50, 64, "Good"),
            ("D", 35, 49, "Pass"),
            ("F", 0, 34, "Fail"),
        ]
        for name, min_s, max_s, remark in grades:
            GradeScale.objects.get_or_create(
                name=name, min_score=min_s, max_score=max_s, grade=name, remark=remark
            )

        # Create Admin User
        admin_user, _ = User.objects.get_or_create(
            username="admin", defaults={
                'email': 'admin@happychild.ac.ug',
                'role': 'admin',
                'first_name': 'School',
                'last_name': 'Admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if not admin_user.check_password('admin123'):
            admin_user.set_password('admin123')
            admin_user.save()

        # Create Headteacher
        head_user, _ = User.objects.get_or_create(
            username="headteacher", defaults={
                'email': 'head@happychild.ac.ug',
                'role': 'headteacher',
                'first_name': 'John',
                'last_name': 'Okello',
            }
        )
        if not head_user.check_password('head123'):
            head_user.set_password('head123')
            head_user.save()

        # Teachers with practical per-class subject assignments
        teacher_assignments = [
            ("teacher1", "Mary", "Achieng", [
                ("Primary 1", ["Mathematics", "Science"]),
                ("Primary 2", ["Mathematics", "Science"]),
            ]),
            ("teacher2", "Peter", "Ochieng", [
                ("Primary 1", ["English", "Social Studies"]),
                ("Primary 3", ["English", "Social Studies"]),
            ]),
            ("teacher3", "Grace", "Atim", [
                ("Primary 2", ["Kiswahili"]),
                ("Primary 3", ["Kiswahili"]),
            ]),
        ]
        teachers = []
        class_by_name = {c.name: c for c in classes}
        for uname, fname, lname, class_subjects in teacher_assignments:
            tuser, _ = User.objects.get_or_create(
                username=uname, defaults={
                    'email': f'{uname}@happychild.ac.ug',
                    'role': 'teacher',
                    'first_name': fname,
                    'last_name': lname,
                }
            )
            if not tuser.check_password('teacher123'):
                tuser.set_password('teacher123')
                tuser.save()

            teacher, _ = Teacher.objects.get_or_create(
                user=tuser,
                defaults={
                    'first_name': fname,
                    'last_name': lname,
                    'qualification': 'Bachelor of Education',
                }
            )
            teacher.subjects_taught.clear()
            for class_name, subj_names in class_subjects:
                cls = class_by_name.get(class_name)
                if not cls:
                    continue
                for subj in subjects_by_class.get(cls, []):
                    if subj.name in subj_names:
                        teacher.subjects_taught.add(subj)
                        subj.teacher = tuser
                        subj.save(update_fields=['teacher'])
            teachers.append(teacher)

        # Spread students across assigned classes
        target_classes = [class_by_name[n] for n in ("Primary 1", "Primary 2", "Primary 3") if n in class_by_name]

        # Create Students (distributed in Primary 1–3 for teacher demos)
        students = []
        for i in range(1, 21):
            cls = target_classes[(i - 1) % len(target_classes)] if target_classes else random.choice(classes)
            student, created = Student.objects.get_or_create(
                first_name=f'Student{i}',
                last_name='Demo',
                defaults={
                    'date_of_birth': date(2015, 5, 15),
                    'current_class': cls,
                    'emergency_contact': '+256712345678',
                }
            )
            if not created and target_classes:
                student.current_class = cls
                student.save(update_fields=['current_class'])
            students.append(student)

        # Assign some parents
        for i, student in enumerate(students[:10]):
            puser, _ = User.objects.get_or_create(
                username=f"parent{i+1}", defaults={
                    'email': f'parent{i+1}@example.com',
                    'role': 'parent',
                    'first_name': f'Parent{i+1}',
                    'last_name': 'Demo',
                }
            )
            if not puser.check_password('parent123'):
                puser.set_password('parent123')
                puser.save()
            student.parent = puser
            student.save()

        # Exams & marks — one mid-term per assigned subject/class
        for teacher in teachers:
            for subj in teacher.subjects_taught.all():
                cls = subj.class_room
                exam, _ = Exam.objects.get_or_create(
                    name=f'Mid-Term {term1.name}',
                    term=term1,
                    subject=subj,
                    class_room=cls,
                    defaults={
                        'start_date': date(2025, 10, 15),
                        'end_date': date(2025, 10, 20),
                        'max_marks': 100,
                        'is_published': True,
                    },
                )
                class_students = [s for s in students if s.current_class_id == cls.id]
                for stud in class_students:
                    ExamResult.objects.update_or_create(
                        exam=exam,
                        student=stud,
                        defaults={
                            'marks_obtained': random.randint(45, 96),
                            'remarks': random.choice(['Good effort', 'Keep it up', 'Well done', '']),
                        },
                    )

        # Continuous assessment demo marks (teacher-editable per subject)
        for teacher in teachers:
            for subj in teacher.subjects_taught.all():
                for stud in students:
                    if stud.current_class_id != subj.class_room_id:
                        continue
                    StudentResult.objects.update_or_create(
                        student=stud,
                        subject=subj,
                        term=term1,
                        defaults={
                            'test_score': random.randint(10, 25),
                            'exam_score': random.randint(30, 70),
                            'grade': random.choice(['A', 'B', 'C', 'D']),
                        },
                    )

        # Create Lesson Plans for teachers
        for teacher in teachers:
            for subj in teacher.subjects_taught.all()[:2]:
                cls = random.choice(classes)
                LessonPlan.objects.get_or_create(
                    teacher=teacher,
                    subject=subj,
                    class_room=cls,
                    date=date(2025, 10, 10),
                    defaults={
                        'topic': f"Introduction to {subj.name}",
                        'objectives': "Understand basic concepts",
                        'activities': "Group work, discussion",
                        'resources': "Textbook, whiteboard",
                        'assessment': "Quiz at end of lesson",
                    }
                )

        # Create TimeSlots and Timetable
        time_slots = []
        for day in ['MON', 'TUE', 'WED', 'THU', 'FRI']:
            for start, end in [('08:00','09:00'), ('09:00','10:00'), ('10:00','11:00')]:
                slot, _ = TimeSlot.objects.get_or_create(day=day, start_time=start, end_time=end)
                time_slots.append(slot)

        slot_offset = 0
        for cls in target_classes or classes[:2]:
            class_subjects = subjects_by_class.get(cls, [])[:3]
            for i, subj in enumerate(class_subjects):
                slot_idx = slot_offset + i
                if slot_idx >= len(time_slots):
                    continue
                assigned_teacher = None
                if subj.teacher_id:
                    try:
                        assigned_teacher = subj.teacher.teacher_profile
                    except Exception:
                        assigned_teacher = None
                if not assigned_teacher:
                    assigned_teacher = next(
                        (t for t in teachers if subj in t.subjects_taught.all()),
                        random.choice(teachers),
                    )
                TimetableEntry.objects.update_or_create(
                    class_room=cls,
                    time_slot=time_slots[slot_idx],
                    term=term1,
                    defaults={
                        'subject': subj,
                        'teacher': assigned_teacher,
                    },
                )
            slot_offset += 3

        # Create Events
        Event.objects.get_or_create(
            title="Sports Day",
            defaults={
                'description': "Annual sports day for all classes.",
                'date': date(2025, 11, 15),
                'location': "School Playground",
                'is_upcoming': True,
            }
        )
        Event.objects.get_or_create(
            title="Parents Meeting",
            defaults={
                'description': "Termly parents-teachers meeting.",
                'date': date(2025, 11, 20),
                'location': "Main Hall",
                'is_upcoming': True,
            }
        )

        # Create some Fee Structures
        for cls in classes[:3]:
            FeeStructure.objects.get_or_create(
                name="Tuition Fee",
                academic_year=year,
                class_room=cls,
                defaults={'amount': 150000}
            )

        # Staff members (all teachers + headteacher + bursar) and demo payroll
        self.stdout.write("Creating staff and payroll demo data...")
        try:
            from staff.demo_data import populate_staff_and_payroll
            populate_staff_and_payroll(stdout=self.stdout)
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Staff/payroll demo skipped: {exc}"))

        self.stdout.write(self.style.SUCCESS("Demo data populated successfully!"))
        self.stdout.write("Login users:")
        self.stdout.write("  admin / admin123 (admin)")
        self.stdout.write("  headteacher / head123 (headteacher)")
        self.stdout.write("  teacher1 / teacher123 — Maths & Science P1–P2")
        self.stdout.write("  teacher2 / teacher123 — English & SST P1, P3")
        self.stdout.write("  teacher3 / teacher123 — Kiswahili P2–P3")
        self.stdout.write("  Teacher marks hub: /examinations/teacher/marks/")
        self.stdout.write("  teacher2 / teacher123 (teacher)")
        self.stdout.write("  teacher3 / teacher123 (teacher)")
        self.stdout.write("  bursar / bursar123 (bursar)")
        self.stdout.write("  parent1 / parent123 (example parent)")
        self.stdout.write("")
        self.stdout.write("Staff payroll: /staff/  |  My Payroll: /staff/my-payroll/")