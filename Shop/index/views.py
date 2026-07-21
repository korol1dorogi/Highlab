from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST

from .models import ServiceCard, Advantage, CompanyStat, Partner, Landing
from .forms import LeadForm, QuickLeadForm, LEAD_CAPTCHA_KEY
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


@require_POST
def quick_lead(request):
    """Приём быстрой заявки (обратный звонок / квиз / посадочная страница).

    Без капчи. Защита от ботов: honeypot + отсечение слишком быстрого сабмита
    (люди не заполняют форму за доли секунды). Уведомление уходит в Telegram.
    """
    # Слишком быстрый сабмит (< 1.2 c) при наличии таймера — почти наверняка бот.
    try:
        elapsed = int(request.POST.get('elapsed', '0'))
    except (TypeError, ValueError):
        elapsed = 0
    if 0 < elapsed < 1200:
        return JsonResponse({'success': False, 'message': 'Слишком быстро. Попробуйте ещё раз.'}, status=400)

    form = QuickLeadForm(request.POST)
    if form.is_valid():
        lead = form.save()
        send_lead_notification.delay(lead.id)
        return JsonResponse({
            'success': True,
            'message': 'Спасибо! Заявка принята — перезвоним в ближайшее время.',
        })

    if 'website' in form.errors:
        # honeypot сработал — отвечаем «успехом», чтобы бот не подбирал
        return JsonResponse({'success': True, 'message': 'Спасибо! Заявка принята.'})
    return JsonResponse({
        'success': False,
        'errors': form.errors,
        'message': 'Проверьте телефон — он обязателен.',
    }, status=400)


def landing(request, slug):
    """Посадочная страница под контекстную рекламу (/lp/<slug>/)."""
    lp = get_object_or_404(Landing, slug=slug, is_active=True)
    return render(request, 'landing.html', {'landing': lp})
