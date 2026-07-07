"""Resolve school logo from media/logo/."""
from django.conf import settings

_LOGO_SUBDIR = 'logo'
_PREFERRED_NAMES = ('image.png', 'logo.png', 'school_logo.png')
_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}


def get_school_logo_filename():
    logo_dir = settings.MEDIA_ROOT / _LOGO_SUBDIR
    if not logo_dir.is_dir():
        return None
    for name in _PREFERRED_NAMES:
        if (logo_dir / name).is_file():
            return name
    for path in sorted(logo_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in _IMAGE_EXTENSIONS:
            return path.name
    return None


def get_school_logo_url():
    filename = get_school_logo_filename()
    if not filename:
        return None
    return f'{settings.MEDIA_URL}{_LOGO_SUBDIR}/{filename}'


def get_school_logo_path():
    filename = get_school_logo_filename()
    if not filename:
        return None
    return settings.MEDIA_ROOT / _LOGO_SUBDIR / filename