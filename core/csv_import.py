"""CSV import handlers for bulk data loading."""
import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction

from academics.models import StudentResult
from core.models import ClassRoom, Term, Subject
from examinations.models import Exam, ExamResult
from fees.models import Payment, FeeStructure
from students.models import Student


def _decode_file(uploaded_file):
    raw = uploaded_file.read()
    for encoding in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode('utf-8', errors='replace')


def _parse_csv(uploaded_file):
    text = _decode_file(uploaded_file)
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError('CSV file has no header row.')
    # Normalize headers: strip whitespace and lowercase
    rows = []
    for row in reader:
        cleaned = {k.strip().lower().replace(' ', '_'): (v or '').strip() for k, v in row.items() if k}
        if any(cleaned.values()):
            rows.append(cleaned)
    return rows


def _parse_date(value):
    if not value:
        return None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f'Invalid date format: {value}. Use YYYY-MM-DD or DD/MM/YYYY.')


def _parse_decimal(value, field_name='value'):
    if value in ('', None):
        return Decimal('0')
    try:
        return Decimal(str(value).replace(',', ''))
    except InvalidOperation as exc:
        raise ValueError(f'Invalid number for {field_name}: {value}') from exc


def _resolve_class(class_name):
    classroom = ClassRoom.objects.filter(name__iexact=class_name).first()
    if not classroom:
        raise ValueError(f'Class not found: {class_name}')
    return classroom


def _resolve_student(student_id=None, first_name=None, last_name=None):
    if student_id:
        student = Student.objects.filter(student_id__iexact=student_id).first()
        if student:
            return student
        raise ValueError(f'Student not found with ID: {student_id}')
    if first_name and last_name:
        student = Student.objects.filter(
            first_name__iexact=first_name, last_name__iexact=last_name
        ).first()
        if student:
            return student
        raise ValueError(f'Student not found: {first_name} {last_name}')
    raise ValueError('Provide student_id or first_name + last_name.')


def import_students(uploaded_file):
    rows = _parse_csv(uploaded_file)
    created = updated = errors = 0
    error_details = []

    with transaction.atomic():
        for i, row in enumerate(rows, start=2):
            try:
                first_name = row.get('first_name') or row.get('firstname')
                last_name = row.get('last_name') or row.get('lastname')
                if not first_name or not last_name:
                    raise ValueError('first_name and last_name are required.')

                dob = _parse_date(row.get('date_of_birth') or row.get('dob'))
                if not dob:
                    raise ValueError('date_of_birth is required.')

                gender = (row.get('gender') or 'M').upper()
                if gender in ('MALE', 'BOY'):
                    gender = 'M'
                elif gender in ('FEMALE', 'GIRL'):
                    gender = 'F'

                classroom = None
                class_name = row.get('class') or row.get('class_name') or row.get('current_class')
                if class_name:
                    classroom = _resolve_class(class_name)

                student_id = row.get('student_id') or row.get('id')
                defaults = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'date_of_birth': dob,
                    'gender': gender,
                    'current_class': classroom,
                    'emergency_contact': row.get('emergency_contact', ''),
                    'address': row.get('address', ''),
                    'is_active': row.get('is_active', 'true').lower() not in ('false', '0', 'no'),
                }

                if student_id:
                    student, was_created = Student.objects.update_or_create(
                        student_id=student_id, defaults=defaults
                    )
                else:
                    student = Student.objects.create(**defaults)
                    was_created = True

                if was_created:
                    created += 1
                else:
                    updated += 1
            except Exception as exc:
                errors += 1
                error_details.append(f'Row {i}: {exc}')

    return {
        'created': created, 'updated': updated, 'errors': errors,
        'error_details': error_details[:20],
        'total_rows': len(rows),
    }


def import_exam_marks(uploaded_file, exam_id=None):
    rows = _parse_csv(uploaded_file)
    created = updated = errors = 0
    error_details = []

    with transaction.atomic():
        for i, row in enumerate(rows, start=2):
            try:
                student = _resolve_student(
                    row.get('student_id'),
                    row.get('first_name'),
                    row.get('last_name'),
                )
                marks = _parse_decimal(
                    row.get('marks') or row.get('marks_obtained') or row.get('score'),
                    'marks',
                )

                exam = None
                if exam_id:
                    exam = Exam.objects.get(pk=exam_id)
                else:
                    exam_name = row.get('exam') or row.get('exam_name')
                    subject_name = row.get('subject') or row.get('subject_name')
                    if not exam_name or not subject_name:
                        raise ValueError('exam and subject columns required (or select exam above).')
                    exam = Exam.objects.filter(
                        name__iexact=exam_name,
                        subject__name__iexact=subject_name,
                    ).first()
                    if not exam:
                        raise ValueError(f'Exam not found: {exam_name} / {subject_name}')

                result, was_created = ExamResult.objects.update_or_create(
                    exam=exam, student=student,
                    defaults={
                        'marks_obtained': marks,
                        'remarks': row.get('remarks', ''),
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            except Exception as exc:
                errors += 1
                error_details.append(f'Row {i}: {exc}')

    return {
        'created': created, 'updated': updated, 'errors': errors,
        'error_details': error_details[:20],
        'total_rows': len(rows),
    }


def import_continuous_assessment(uploaded_file):
    rows = _parse_csv(uploaded_file)
    created = updated = errors = 0
    error_details = []

    with transaction.atomic():
        for i, row in enumerate(rows, start=2):
            try:
                student = _resolve_student(
                    row.get('student_id'),
                    row.get('first_name'),
                    row.get('last_name'),
                )
                subject_name = row.get('subject') or row.get('subject_name')
                term_name = row.get('term') or row.get('term_name')
                if not subject_name or not term_name:
                    raise ValueError('subject and term are required.')

                subject = Subject.objects.filter(name__iexact=subject_name).first()
                if not subject:
                    raise ValueError(f'Subject not found: {subject_name}')
                term = Term.objects.filter(name__iexact=term_name).first()
                if not term:
                    raise ValueError(f'Term not found: {term_name}')

                test_score = _parse_decimal(row.get('test_score') or row.get('test'), 'test_score')
                exam_score = _parse_decimal(row.get('exam_score') or row.get('exam'), 'exam_score')
                grade = row.get('grade', '')

                result, was_created = StudentResult.objects.update_or_create(
                    student=student, subject=subject, term=term,
                    defaults={
                        'test_score': test_score,
                        'exam_score': exam_score,
                        'grade': grade,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            except Exception as exc:
                errors += 1
                error_details.append(f'Row {i}: {exc}')

    return {
        'created': created, 'updated': updated, 'errors': errors,
        'error_details': error_details[:20],
        'total_rows': len(rows),
    }


def import_payments(uploaded_file, recorded_by=None):
    rows = _parse_csv(uploaded_file)
    created = errors = 0
    error_details = []
    method_map = {
        'cash': 'cash', 'bank': 'bank', 'bank_transfer': 'bank',
        'cheque': 'cheque', 'check': 'cheque',
        'mtn': 'mtn_momo', 'mtn_momo': 'mtn_momo', 'mtn_mobile_money': 'mtn_momo',
        'airtel': 'airtel_money', 'airtel_money': 'airtel_money',
        'mobile': 'mobile_money', 'mobile_money': 'mobile_money',
    }

    with transaction.atomic():
        for i, row in enumerate(rows, start=2):
            try:
                student = _resolve_student(
                    row.get('student_id'),
                    row.get('first_name'),
                    row.get('last_name'),
                )
                amount = _parse_decimal(
                    row.get('amount') or row.get('amount_paid'), 'amount'
                )
                if amount <= 0:
                    raise ValueError('amount must be greater than zero.')

                method_raw = (row.get('payment_method') or row.get('method') or 'cash').lower()
                payment_method = method_map.get(method_raw, 'cash')

                fee_structure = None
                fee_name = row.get('fee_structure') or row.get('fee_item') or row.get('fee')
                if fee_name:
                    fee_structure = FeeStructure.objects.filter(name__iexact=fee_name).first()

                payment = Payment(
                    student=student,
                    fee_structure=fee_structure,
                    amount_paid=amount,
                    payment_method=payment_method,
                    remarks=row.get('remarks', ''),
                    recorded_by=recorded_by,
                )
                date_str = row.get('date') or row.get('date_paid')
                if date_str:
                    payment.date_paid = _parse_date(date_str)
                payment.save()
                created += 1
            except Exception as exc:
                errors += 1
                error_details.append(f'Row {i}: {exc}')

    return {
        'created': created, 'updated': 0, 'errors': errors,
        'error_details': error_details[:20],
        'total_rows': len(rows),
    }


IMPORT_TYPES = {
    'students': {
        'label': 'Students',
        'handler': import_students,
        'columns': 'first_name, last_name, date_of_birth, gender, class, student_id (optional), emergency_contact, address',
        'sample': 'first_name,last_name,date_of_birth,gender,class\nJohn,Doe,2015-03-15,Male,Primary 5',
    },
    'exam_marks': {
        'label': 'Exam Marks',
        'handler': import_exam_marks,
        'columns': 'student_id, marks, exam, subject, remarks (or select exam and use student_id + marks)',
        'sample': 'student_id,marks,exam,subject\nHCN/2026/001,85,Mid-Term,Mathematics',
        'needs_exam': True,
    },
    'continuous_assessment': {
        'label': 'Continuous Assessment',
        'handler': import_continuous_assessment,
        'columns': 'student_id, subject, term, test_score, exam_score, grade',
        'sample': 'student_id,subject,term,test_score,exam_score,grade\nHCN/2026/001,Mathematics,Term 1,20,60,B',
    },
    'payments': {
        'label': 'Fee Payments',
        'handler': import_payments,
        'columns': 'student_id, amount, payment_method, fee_structure, date, remarks',
        'sample': 'student_id,amount,payment_method,fee_structure,date\nHCN/2026/001,150000,cash,Tuition,2026-01-15',
    },
}