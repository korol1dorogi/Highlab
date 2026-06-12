from .models import SiteSettings, TeamContact


def site_settings(request):
    """Делает настройки сайта и контакты доступными во всех шаблонах (например, в подвале)."""
    return {
        'site_settings': SiteSettings.load(),
        'team_contacts': TeamContact.objects.filter(is_active=True),
    }
