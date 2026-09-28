import json
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import MISSING, STATUS_LABELS, Job, MonitoredCompany, MonitoredHost, Report, Status
from .services import ReportError, ingest

MAX_BODY = 512 * 1024


def _token(request):
    auth = request.headers.get('Authorization', '')
    if auth.lower().startswith('bearer '):
        return auth[7:].strip()
    return request.headers.get('X-Monitor-Token', '').strip()


def _client_ip(request):
    # nginx проставляет X-Real-IP / X-Forwarded-For; Django наружу не торчит.
    ip = request.headers.get('X-Real-IP') or request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
    return ip or request.META.get('REMOTE_ADDR')


@csrf_exempt
@require_POST
def api_report(request):
    """Приём отчётов от PowerShell-скриптов на серверах клиентов.

    Авторизация: заголовок `Authorization: Bearer <токен сервера>`.
    Формат тела — см. deploy/monitoring/README.md.
    """
    token = _token(request)
    host = MonitoredHost.objects.select_related('company').filter(token=token).first() if token else None
    if host is None or not host.is_active or not host.company.is_active:
        return JsonResponse({'ok': False, 'error': 'неверный или отключённый токен'}, status=401)

    if len(request.body) > MAX_BODY:
        return JsonResponse({'ok': False, 'error': 'слишком большой запрос'}, status=413)
    try:
        payload = json.loads(request.body.decode('utf-8-sig'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({'ok': False, 'error': 'тело запроса — не JSON в UTF-8'}, status=400)

    try:
        saved, errors = ingest(host, payload, ip=_client_ip(request))
    except ReportError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

    return JsonResponse({'ok': bool(saved), 'accepted': len(saved), 'errors': errors},
                        status=200 if saved else 400)


@staff_member_required
def dashboard(request):
    now = timezone.now()
    companies = (MonitoredCompany.objects.filter(is_active=True)
                 .prefetch_related('hosts__jobs'))

    counters = {s: 0 for s in (Status.ERROR, MISSING, Status.WARNING, Status.OK)}
    groups = []
    for company in companies:
        hosts = []
        for host in company.hosts.all():
            if not host.is_active:
                continue
            jobs = []
            for job in host.jobs.all():
                if not job.is_active:
                    continue
                job.status_now = job.current_status(now)
                counters[job.status_now] += 1
                jobs.append(job)
            hosts.append({'host': host, 'jobs': jobs})
        groups.append({'company': company, 'hosts': hosts})

    reports = Report.objects.select_related('job__host__company')
    status = request.GET.get('status', '')
    if status in Status.values:
        reports = reports.filter(status=status)
    company_id = request.GET.get('company', '')
    if company_id.isdigit():
        reports = reports.filter(job__host__company_id=company_id)
    days = request.GET.get('days', '7')
    days = int(days) if days.isdigit() and 0 < int(days) <= 365 else 7
    reports = reports.filter(received_at__gte=now - timedelta(days=days))

    page = Paginator(reports, 100).get_page(request.GET.get('page'))
    query = request.GET.copy()
    query.pop('page', None)

    return render(request, 'monitoring/dashboard.html', {
        'groups': groups,
        'counters': [(s, STATUS_LABELS[s], n) for s, n in counters.items()],
        'page': page,
        'query': query.urlencode(),
        'filters': {'status': status, 'company': company_id, 'days': days},
        'statuses': Status.choices,
        'all_companies': MonitoredCompany.objects.all(),
        'now': now,
    })


@staff_member_required
def job_detail(request, pk):
    job = get_object_or_404(Job.objects.select_related('host__company'), pk=pk)
    job.status_now = job.current_status()
    page = Paginator(job.reports.all(), 50).get_page(request.GET.get('page'))
    return render(request, 'monitoring/job_detail.html', {'job': job, 'page': page})
