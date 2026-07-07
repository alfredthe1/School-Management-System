"""Professional report card PDF builder."""
import io
from datetime import date

from django.db.models import Avg, Sum
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from academics.models import StudentResult
from core.branding import get_school_logo_path
from core.models import AcademicYear, Term
from examinations.models import ExamResult
from fees.models import Payment

SCHOOL_BLUE = colors.HexColor('#1B4F72')
SCHOOL_LIGHT = colors.HexColor('#2C7BB6')
ACCENT_GOLD = colors.HexColor('#D4A017')
ROW_ALT = colors.HexColor('#F4F8FB')
BORDER_GREY = colors.HexColor('#BDC3C7')


def _p(text, style):
    return Paragraph(str(text).replace('\n', '<br/>'), style)


def _fmt_ugx(amount):
    try:
        return f'UGX {float(amount):,.0f}'
    except (TypeError, ValueError):
        return 'UGX 0'


def build_report_card_pdf(student, school_info=None, parent_view=False):
    """Build a professional A4 report card PDF and return bytes."""
    school_info = school_info or {}
    school_name = school_info.get('school_name', 'Happy Child Nursery and Primary School')
    school_motto = school_info.get('school_motto', 'Always an achiever')
    current_year = school_info.get('current_academic_year')
    current_term = school_info.get('current_term')

    if not current_year:
        current_year = AcademicYear.objects.filter(is_current=True).first()
    if not current_term:
        current_term = Term.objects.filter(is_current=True).first()

    exam_qs = ExamResult.objects.filter(student=student).select_related(
        'exam__subject', 'exam__term', 'exam__class_room'
    )
    if parent_view:
        exam_qs = exam_qs.filter(exam__is_published=True)
    exam_results = exam_qs.order_by('exam__term__name', 'exam__subject__name')

    ca_results = StudentResult.objects.filter(student=student).select_related(
        'subject', 'term'
    ).order_by('term__name', 'subject__name')

    payments = Payment.objects.filter(student=student)
    total_paid = payments.aggregate(total=Sum('amount_paid'))['total'] or 0
    fee_due = student.get_total_fees_due()
    balance = fee_due - total_paid

    exam_avg = exam_results.aggregate(avg=Avg('marks_obtained'))['avg']
    ca_avg = ca_results.aggregate(avg=Avg('total'))['avg']

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=28,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'SchoolTitle', parent=styles['Heading1'],
        fontSize=16, leading=20, alignment=TA_CENTER,
        textColor=colors.white, fontName='Helvetica-Bold',
    )
    motto_style = ParagraphStyle(
        'Motto', parent=styles['Normal'],
        fontSize=9, alignment=TA_CENTER, textColor=colors.white,
    )
    section_style = ParagraphStyle(
        'Section', parent=styles['Heading2'],
        fontSize=11, textColor=SCHOOL_BLUE, fontName='Helvetica-Bold',
        spaceBefore=6, spaceAfter=4,
    )
    label_style = ParagraphStyle(
        'Label', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold',
    )
    value_style = ParagraphStyle(
        'Value', parent=styles['Normal'], fontSize=9,
    )
    footer_style = ParagraphStyle(
        'Footer', parent=styles['Normal'], fontSize=8,
        textColor=colors.grey, alignment=TA_CENTER,
    )
    elements = []

    # Header band (logo + school title)
    logo_path = get_school_logo_path()
    header_rows = []
    if logo_path:
        try:
            logo = Image(str(logo_path), width=52, height=52)
            logo.hAlign = 'CENTER'
            header_rows.append([logo])
        except Exception:
            pass
    header_rows.extend([
        [_p(f'<b>{school_name}</b>', title_style)],
        [_p(school_motto, motto_style)],
        [_p('OFFICIAL STUDENT REPORT CARD', ParagraphStyle(
            'RC', parent=styles['Normal'], fontSize=10,
            alignment=TA_CENTER, textColor=colors.white, fontName='Helvetica-Bold',
        ))],
    ])
    header_table = Table(header_rows, colWidths=[doc.width])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), SCHOOL_BLUE),
        ('TOPPADDING', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.15 * inch))

    # Student info grid
    gender = 'Male' if student.gender == 'M' else 'Female'
    year_label = current_year.name if current_year else 'N/A'
    term_label = current_term.name if current_term else 'N/A'
    info_rows = [
        [
            _p('<b>Student Name:</b>', label_style),
            _p(student.get_full_name(), value_style),
            _p('<b>Student ID:</b>', label_style),
            _p(student.student_id, value_style),
        ],
        [
            _p('<b>Class:</b>', label_style),
            _p(str(student.current_class or 'Not Assigned'), value_style),
            _p('<b>Gender:</b>', label_style),
            _p(gender, value_style),
        ],
        [
            _p('<b>Date of Birth:</b>', label_style),
            _p(student.date_of_birth.strftime('%d %B %Y'), value_style),
            _p('<b>Academic Year:</b>', label_style),
            _p(year_label, value_style),
        ],
        [
            _p('<b>Term:</b>', label_style),
            _p(term_label, value_style),
            _p('<b>Report Date:</b>', label_style),
            _p(date.today().strftime('%d %B %Y'), value_style),
        ],
    ]
    info_table = Table(info_rows, colWidths=[1.1 * inch, 2.3 * inch, 1.1 * inch, 2.3 * inch])
    info_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, BORDER_GREY),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_GREY),
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.12 * inch))

    # Performance summary
    summary_data = [[
        _p('<b>Exam Average</b>', label_style),
        _p(f'{round(exam_avg, 1)}%' if exam_avg else 'N/A', value_style),
        _p('<b>CA Average</b>', label_style),
        _p(f'{round(ca_avg, 1)}' if ca_avg else 'N/A', value_style),
    ]]
    summary_table = Table(summary_data, colWidths=[1.5 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#EBF5FB')),
        ('BOX', (0, 0), (-1, -1), 1, SCHOOL_LIGHT),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.15 * inch))

    def _marks_table(title, headers, rows):
        elements.append(_p(title, section_style))
        if not rows:
            elements.append(_p('No records available for this section.', value_style))
            elements.append(Spacer(1, 0.1 * inch))
            return
        data = [headers] + rows
        col_count = len(headers)
        width = doc.width / col_count
        table = Table(data, colWidths=[width] * col_count, repeatRows=1)
        style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), SCHOOL_LIGHT),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GREY),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]
        for i in range(1, len(data)):
            if i % 2 == 0:
                style_cmds.append(('BACKGROUND', (0, i), (-1, i), ROW_ALT))
        table.setStyle(TableStyle(style_cmds))
        elements.append(table)
        elements.append(Spacer(1, 0.12 * inch))

    # Exam results
    exam_rows = []
    for r in exam_results:
        exam_rows.append([
            r.exam.term.name if r.exam.term else '—',
            r.exam.subject.name,
            r.exam.name,
            f'{r.marks_obtained}/{r.exam.max_marks}',
            r.grade or '—',
            (r.remarks or '—')[:40],
        ])
    _marks_table(
        'Examination Results',
        ['Term', 'Subject', 'Exam', 'Score', 'Grade', 'Remarks'],
        exam_rows,
    )

    # Continuous assessment
    ca_rows = []
    for r in ca_results:
        ca_rows.append([
            r.term.name,
            r.subject.name,
            str(r.test_score),
            str(r.exam_score),
            str(r.total),
            r.grade or '—',
        ])
    _marks_table(
        'Continuous Assessment',
        ['Term', 'Subject', 'Test', 'Exam', 'Total', 'Grade'],
        ca_rows,
    )

    # Fee summary
    elements.append(_p('Fee Summary', section_style))
    fee_data = [
        ['Description', 'Amount'],
        ['Total Fees Due', _fmt_ugx(fee_due)],
        ['Total Paid', _fmt_ugx(total_paid)],
        ['Outstanding Balance', _fmt_ugx(max(balance, 0))],
    ]
    fee_table = Table(fee_data, colWidths=[doc.width * 0.65, doc.width * 0.35])
    fee_style = [
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT_GOLD),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GREY),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]
    if balance <= 0:
        fee_style.append(('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#D5F5E3')))
    else:
        fee_style.append(('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#FADBD8')))
    fee_table.setStyle(TableStyle(fee_style))
    elements.append(fee_table)
    elements.append(Spacer(1, 0.25 * inch))

    # Signatures
    sig_data = [[
        _p('_' * 28, value_style),
        _p('_' * 28, value_style),
        _p('_' * 28, value_style),
    ], [
        _p('Class Teacher', ParagraphStyle('Sig', parent=value_style, alignment=TA_CENTER)),
        _p('Head Teacher', ParagraphStyle('Sig', parent=value_style, alignment=TA_CENTER)),
        _p("Parent/Guardian", ParagraphStyle('Sig', parent=value_style, alignment=TA_CENTER)),
    ]]
    sig_table = Table(sig_data, colWidths=[doc.width / 3] * 3)
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 1), (-1, 1), 4),
    ]))
    elements.append(sig_table)
    elements.append(Spacer(1, 0.15 * inch))
    elements.append(HRFlowable(width='100%', thickness=0.5, color=BORDER_GREY))
    elements.append(Spacer(1, 0.08 * inch))
    elements.append(_p(
        f'Generated on {date.today().strftime("%d %B %Y")} · {school_name} · Official Academic Record',
        footer_style,
    ))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf