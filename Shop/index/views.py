from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .models import ServiceCard, Advantage, CompanyStat, Partner
from .forms import LeadForm, LEAD_CAPTCHA_KEY
from .tasks import send_lead_notification
from accounts.captcha import new_captcha
from content.models import Project


def index(request):
    context = {
        'service_cards': ServiceCard.objects.filter(is_active=True),
        'advantages': Advantage.objects.filter(is_active=True),
        # Показываем только заполненные цифры — плейсхолдеры «…» и пустые скрываем
        'company_stats': CompanyStat.objects.filter(is_active=True).exclude(value='…').exclude(value=''),
        'latest_projects': Project.objects.filter(is_published=True)[:3],
        'partners': Partner.objects.filter(is_active=True),
        'lead_form': LeadForm(),
        'lead_captcha_question': new_captcha(request.session, key=LEAD_CAPTCHA_KEY),
    }
    return render(request, 'index2_0.html', context)


@require_POST
def lead_create(request):
    """Приём заявки с лендинга (AJAX). Уведомление уходит в Telegram через Celery."""
    form = LeadForm(request.POST, request=request)
    if form.is_valid():
        lead = form.save()
        send_lead_notification.delay(lead.id)
        return JsonResponse({
            'success': True,
            'message': 'Спасибо! Заявка отправлена — мы скоро свяжемся с вами.',
            'captcha_question': new_captcha(request.session, key=LEAD_CAPTCHA_KEY),
        })

    if 'captcha' in form.errors:
        message = 'Неверный ответ на проверочный вопрос. Попробуйте ещё раз.'
    elif 'website' in form.errors:
        message = 'Не удалось отправить.'
    else:
        message = 'Проверьте поля: имя и телефон обязательны.'
    return JsonResponse({
        'success': False,
        'errors': form.errors,
        'message': message,
        'captcha_question': new_captcha(request.session, key=LEAD_CAPTCHA_KEY),
    }, status=400)
