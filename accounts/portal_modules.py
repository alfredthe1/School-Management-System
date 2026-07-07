"""Portal module registry — defines what users can access in the system."""

# module_code: (label, category, icon, default roles with access)
PORTAL_MODULES = {
    'dashboard': ('Dashboard', 'general', 'bi-speedometer2', ['admin', 'headteacher', 'teacher', 'bursar']),
    'students': ('Students', 'academic', 'bi-people', ['admin', 'headteacher', 'teacher', 'bursar']),
    'teachers': ('Teachers', 'academic', 'bi-person-badge', ['admin', 'headteacher']),
    'staff_payroll': ('Staff & Payroll', 'admin', 'bi-person-workspace', ['admin', 'headteacher']),
    'school_structure': ('Classes & Subjects', 'academic', 'bi-diagram-3', ['admin', 'headteacher']),
    'academics': ('Academics', 'academic', 'bi-book', ['admin', 'headteacher', 'teacher']),
    'examinations': ('Examinations', 'academic', 'bi-clipboard-check', ['admin', 'headteacher', 'teacher']),
    'fees': ('Fees Management', 'finance', 'bi-wallet2', ['admin', 'headteacher', 'bursar']),
    'payment_gateway': ('Payment Gateway', 'finance', 'bi-phone-vibrate', ['admin']),
    'communication': ('Communication', 'admin', 'bi-broadcast', ['admin', 'headteacher', 'teacher', 'bursar', 'parent']),
    'announcements': ('Announcements', 'general', 'bi-megaphone', ['admin', 'headteacher', 'teacher', 'bursar', 'parent']),
    'reports': ('Reports & Import', 'admin', 'bi-bar-chart', ['admin', 'headteacher']),
    'landing_images': ('Landing Images', 'admin', 'bi-image', ['admin', 'headteacher']),
    'system_users': ('System Users', 'admin', 'bi-shield-lock', ['admin']),
    'parent_dashboard': ('Parent Dashboard', 'parent', 'bi-speedometer2', ['parent']),
    'parent_children': ('My Children', 'parent', 'bi-people', ['parent']),
    'parent_pay_fees': ('Pay School Fees', 'parent', 'bi-wallet2', ['parent']),
    'parent_payment_history': ('Payment History', 'parent', 'bi-receipt', ['parent']),
    'parent_link_child': ('Link a Child', 'parent', 'bi-link-45deg', ['parent']),
    'parent_progress': ('Child Progress', 'parent', 'bi-graph-up', ['parent']),
    'my_payroll': ('My Payroll', 'finance', 'bi-cash-stack', ['teacher', 'bursar', 'admin', 'headteacher']),
}

CATEGORIES = {
    'general': 'General',
    'academic': 'Academic',
    'finance': 'Finance',
    'admin': 'Administration',
    'parent': 'Parent Portal',
}


def default_access_for_role(role, module_code):
    if role == 'admin':
        return True
    meta = PORTAL_MODULES.get(module_code)
    if not meta:
        return False
    return role in meta[3]


def modules_for_role(role):
    return {
        code: meta
        for code, meta in PORTAL_MODULES.items()
        if default_access_for_role(role, code)
    }