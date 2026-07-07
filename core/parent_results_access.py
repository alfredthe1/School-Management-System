"""Whether parents may view a child's academic results (fee-balance policy)."""
from core.models import SchoolPortalSettings


def parent_can_view_results(student):
    """
    Return True if the parent portal may show results for this student.
    Per-student override takes precedence over the school-wide policy.
    """
    override = getattr(student, 'parent_results_access', 'default')
    if override == 'allow':
        return True
    if override == 'block':
        return False

    settings = SchoolPortalSettings.get_solo()
    if not settings.block_parent_results_on_fee_balance:
        return True

    return student.get_fees_balance() <= 0


def parent_results_blocked_reason(student):
    """Human-readable reason when results are hidden from parents."""
    override = getattr(student, 'parent_results_access', 'default')
    if override == 'block':
        return 'Results access has been restricted by the school administration.'
    if override == 'allow':
        return ''

    settings = SchoolPortalSettings.get_solo()
    balance = student.get_fees_balance()
    if settings.block_parent_results_on_fee_balance and balance > 0:
        return (
            f'Results are hidden while an outstanding fee balance of '
            f'UGX {balance:,.0f} remains. Please clear fees to view results.'
        )
    return ''


def effective_access_label(student):
    """Label for admin tables: Allowed / Blocked."""
    return 'Allowed' if parent_can_view_results(student) else 'Blocked'