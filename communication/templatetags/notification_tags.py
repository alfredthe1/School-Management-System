from django import template

register = template.Library()

PRIORITY_BADGE = {
    'urgent': 'danger',
    'high': 'warning text-dark',
    'medium': 'primary',
    'low': 'secondary',
}

ANNOUNCEMENT_PRIORITY_ICON = {
    'urgent': 'bi-exclamation-octagon-fill',
    'high': 'bi-exclamation-triangle-fill',
    'medium': 'bi-megaphone-fill',
    'low': 'bi-info-circle-fill',
}


@register.filter
def priority_badge(priority):
    return PRIORITY_BADGE.get(priority, 'secondary')


@register.filter
def announcement_icon(priority):
    return ANNOUNCEMENT_PRIORITY_ICON.get(priority, 'bi-megaphone-fill')