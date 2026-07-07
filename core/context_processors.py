from .models import AcademicYear, Term
from core.models import SchoolTheme
from core.branding import get_school_logo_url

def school_info(request):
    current_year = AcademicYear.objects.filter(is_current=True).first()
    current_term = Term.objects.filter(is_current=True).first()
    return {
        'school_name': 'Happy Child Nursery and Primary School',
        'school_short_name': 'Happy Child Nursery & Primary',
        'school_motto': 'Always an achiever',
        'school_mission': 'To educate the Child to be a patriotic self reliant and God-fearing citizen in the contemporary world',
        'school_logo_url': get_school_logo_url(),
        'current_academic_year': current_year,
        'current_term': current_term,
    }

# core/context_processors.py
def theme_settings(request):
    theme = SchoolTheme.objects.filter(is_active=True).first()
    return {'theme': theme}


def parent_sidebar(request):
    """Children and fee balances for parent sidebar navigation."""
    if not request.user.is_authenticated or request.user.role != 'parent':
        return {}
    from students.models import Student
    children = Student.objects.filter(
        parent=request.user, is_active=True
    ).select_related('current_class').order_by('first_name')
    children_nav = []
    for child in children:
        children_nav.append({
            'student': child,
            'balance': child.get_fees_balance(),
        })
    return {'parent_children_nav': children_nav}


def staff_nav(request):
    """Staff profile for payroll sidebar link."""
    if not request.user.is_authenticated:
        return {}
    from staff.models import StaffMember
    profile = StaffMember.objects.filter(user=request.user, is_active=True).first()
    return {'user_staff_profile': profile}