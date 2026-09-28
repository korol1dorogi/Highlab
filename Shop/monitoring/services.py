"""Приём отчётов от серверов клиентов и сборка сообщений для Telegram."""
import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.html import escape

from .models import MISSING, Job, MonitoredCompany, Report, Status

logger = logging.getLogger(__name__)

TELEGRAM_LIMIT = 4000  # у Telegram предел 4096 символов на сообщение, оставляем запас
MESSAGE_LIMIT = 4000   # сколько символов сообщения от скрипта храним
DETAILS_LIMIT = 50_000  # размер JSON с подробностями (в символах)


class ReportError(ValueError):
    pass


# --- Приём отчётов ------------------------------------------------------------

def _parse_dt(value, field):
    if value in (None, ''):
        return None
    dt = parse_datetime(str(value))
    if dt is None:
        raise ReportError(f'{field}: неверный формат даты, нужен ISO 8601')
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt


def _clean(item):
    """Проверяет один отчёт из запроса и приводит его к полям моделей."""
    if not isinstance(item, dict):
        raise ReportError('отчёт должен быть JSON-объектом')

    name = str(item.get('job') or '').strip()
    if not name:
        raise ReportError('не указано поле job')
    if len(name) > 160:
        raise ReportError('job длиннее 160 символов')

    status = str(item.get('status') or '').strip().lower()
    if status not in Status.values:
        raise ReportError(f'{name}: status должен быть ok, warning или error')

    kind = str(item.get('kind') or Job.Kind.BACKUP).lower()
    if kind not in Job.Kind.values:
        kind = Job.Kind.CHECK
    engine = str(item.get('engine') or '').lower()
    if engine and engine not in Job.Engine.values:
        engine = Job.Engine.OTHER

    size = item.get('size_bytes')
    if size not in (None, ''):
        try:
            size = int(size)
        except (TypeError, ValueError):
            raise ReportError(f'{name}: size_bytes должно быть числом')
    else:
        size = None

    every = item.get('expected_every_hours')
    if every not in (None, ''):
        try:
            every = max(1, int(every))
        except (TypeError, ValueError):
            raise ReportError(f'{name}: expected_every_hours должно быть числом')
    else:
        every = None

    details = item.get('details') or {}
    if not isinstance(details, dict):
        details = {'value': details}
    if len(str(details)) > DETAILS_LIMIT:
        details = {'truncated': True, 'note': 'подробности превысили лимит и отброшены'}

    return {
        'name': name,
        'kind': kind,
        'engine': engine,
        'database': str(item.get('database') or '')[:160],
        'expected_every_hours': every,
        'status': status,
        'message': str(item.get('message') or '')[:MESSAGE_LIMIT],
        'started_at': _parse_dt(item.get('started_at'), 'started_at'),
        'finished_at': _parse_dt(item.get('finished_at'), 'finished_at'),
        'size_bytes': size,
        'path': str(item.get('path') or '')[:500],
        'details': details,
    }


def ingest(host, payload, ip=None):
    """Сохраняет отчёты из запроса сервера.

    payload — либо один отчёт, либо {"host": {...}, "reports": [...]}.
    Возвращает (сохранённые отчёты, список ошибок по отклонённым).
    """
    if not isinstance(payload, dict):
        raise ReportError('тело запроса должно быть JSON-объектом')
    items = payload.get('reports') if 'reports' in payload else [payload]
    if not isinstance(items, list) or not items:
        raise ReportError('reports должен быть непустым списком')
    if len(items) > 100:
        raise ReportError('не больше 100 отчётов за запрос')

    now = timezone.now()
    saved, errors, alerts = [], [], []
    with transaction.atomic():
        for item in items:
            try:
                data = _clean(item)
            except ReportError as exc:
                errors.append(str(exc))
                continue

            job, _ = Job.objects.select_for_update().get_or_create(
                host=host, name=data['name'],
                defaults={'kind': data['kind'], 'engine': data['engine'], 'database': data['database']},
            )
            previous = job.last_status
            report = Report.objects.create(
                job=job, received_at=now, status=data['status'], message=data['message'],
                started_at=data['started_at'], finished_at=data['finished_at'],
                size_bytes=data['size_bytes'], path=data['path'], details=data['details'],
            )
            job.kind, job.last_status, job.last_report_at = data['kind'], data['status'], now
            if data['engine']:
                job.engine = data['engine']
            if data['database']:
                job.database = data['database']
            if data['expected_every_hours']:
                job.expected_every_hours = data['expected_every_hours']
            job.save()
            saved.append(report)

            if data['status'] == Status.ERROR:
                alerts.append(report.pk)
            elif data['status'] == Status.OK and previous == Status.ERROR:
                alerts.append(report.pk)

        info = payload.get('host') if isinstance(payload.get('host'), dict) else {}
        host.hostname = str(info.get('hostname') or host.hostname)[:120]
        host.os_info = str(info.get('os') or host.os_info)[:200]
        host.agent_version = str(info.get('agent_version') or host.agent_version)[:40]
        host.last_seen_at = now
        host.last_ip = ip or host.last_ip
        host.save(update_fields=['hostname', 'os_info', 'agent_version', 'last_seen_at', 'last_ip'])

        if alerts and getattr(settings, 'MONITORING_INSTANT_ALERTS', True):
            from .tasks import send_report_alert
            for pk in alerts:
                transaction.on_commit(lambda pk=pk: send_report_alert.delay(pk))

    return saved, errors


# --- Telegram -----------------------------------------------------------------

def chat_ids():
    return getattr(settings, 'MONITORING_TELEGRAM_CHAT_IDS', None) or getattr(settings, 'TELEGRAM_CHAT_IDS', [])


def split_message(text, limit=TELEGRAM_LIMIT):
    """Режет длинный текст по строкам на куски, которые пролезают в Telegram."""
    chunks, current = [], ''
    for line in text.split('\n'):
        while len(line) > limit:  # одна строка длиннее лимита — режем жёстко
            if current:
                chunks.append(current)
                current = ''
            chunks.append(line[:limit])
            line = line[limit:]
        candidate = f'{current}\n{line}' if current else line
        if len(candidate) > limit:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def send_telegram(text):
    """Отправляет текст всем получателям мониторинга. True, если дошло хоть до одного."""
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    recipients = chat_ids()
    if not token or not recipients:
        logger.warning('Telegram не настроен — сообщение мониторинга не отправлено')
        return False

    url = f'https://api.telegram.org/bot{token}/sendMessage'
    sent_any = False
    for chat_id in recipients:
        ok = True
        for chunk in split_message(text):
            try:
                resp = requests.post(url, json={
                    'chat_id': chat_id, 'text': chunk, 'parse_mode': 'HTML',
                    'disable_web_page_preview': True,
                }, timeout=10)
                if resp.status_code != 200:
                    ok = False
                    logger.error('Telegram вернул %s (chat %s): %s', resp.status_code, chat_id, resp.text[:300])
            except requests.RequestException as exc:
                ok = False
                logger.error('Ошибка отправки в Telegram (chat %s): %s', chat_id, exc)
        sent_any = sent_any or ok
    return sent_any


# --- Форматирование -----------------------------------------------------------

def human_size(n):
    if n is None:
        return ''
    size = float(n)
    for unit in ('Б', 'КБ', 'МБ', 'ГБ', 'ТБ'):
        if size < 1024 or unit == 'ТБ':
            return f'{size:.0f} {unit}' if unit == 'Б' else f'{size:.1f} {unit}'
        size /= 1024


def _local(dt, fmt='%d.%m %H:%M'):
    return timezone.localtime(dt).strftime(fmt) if dt else '—'


def _short(text, limit=300):
    lines = [' '.join(line.split()) for line in (text or '').splitlines()]
    text = '; '.join(line for line in lines if line)
    return text if len(text) <= limit else text[:limit - 1] + '…'


def dashboard_link():
    url = getattr(settings, 'MONITORING_DASHBOARD_URL', '')
    return f'\n\n🔗 <a href="{escape(url)}">Все отчёты</a>' if url else ''


def format_alert(report):
    job = report.job
    host = job.host
    if report.status == Status.ERROR:
        head = '❌ <b>Ошибка бэкапа</b>' if job.kind == Job.Kind.BACKUP else '❌ <b>Проблема на сервере</b>'
    else:
        head = '✅ <b>Восстановилось</b>'
    lines = [
        head,
        f'🏢 {escape(host.company.name)} / {escape(host.name)}',
        f'📋 {escape(job.name)}' + (f' ({escape(job.database)})' if job.database else ''),
        f'⏰ {_local(report.received_at, "%d.%m.%Y %H:%M")}',
    ]
    if report.message:
        lines.append(f'\n💬 {escape(_short(report.message, 1500))}')
    return '\n'.join(lines) + dashboard_link()


def _job_line(job, text):
    db = f' ({escape(job.database)})' if job.database and job.database not in job.name else ''
    return f'  {text} {escape(job.host.name)} / {escape(job.name)}{db}'


def build_digest(period_end=None, hours=24):
    """Сводка за период: что прошло нормально, что с ошибками, по чему нет отчётов."""
    period_end = period_end or timezone.now()
    period_start = period_end - timedelta(hours=hours)
    counters = {Status.OK: 0, Status.WARNING: 0, Status.ERROR: 0, MISSING: 0}
    blocks = []

    companies = MonitoredCompany.objects.filter(is_active=True).prefetch_related('hosts__jobs')
    for company in companies:
        problems, ok_count = [], 0
        for host in company.hosts.all():
            if not host.is_active:
                continue
            if host.last_seen_at is None:
                counters[MISSING] += 1
                problems.append(f'  ⏳ {escape(host.name)}: сервер ещё ни разу не присылал отчёты')
                continue
            for job in host.jobs.all():
                if not job.is_active:
                    continue
                reports = list(job.reports.filter(received_at__gt=period_start, received_at__lte=period_end)
                               .order_by('received_at'))
                if not reports:
                    if job.current_status(period_end) == MISSING:
                        counters[MISSING] += 1
                        problems.append(_job_line(job, '⏳') + f' — нет отчёта с {_local(job.last_report_at)}')
                    else:
                        # Задание реже, чем раз в сутки (напр. еженедельное), и срок ещё не вышел.
                        ok_count += 1
                        counters[Status.OK] += 1
                    continue

                last = reports[-1]
                failed = [r for r in reports if r.status == Status.ERROR]
                if last.status == Status.ERROR:
                    counters[Status.ERROR] += 1
                    msg = f': {escape(_short(last.message))}' if last.message else ''
                    problems.append(_job_line(job, '❌') + f' — {_local(last.received_at)}{msg}')
                elif last.status == Status.WARNING:
                    counters[Status.WARNING] += 1
                    msg = f': {escape(_short(last.message))}' if last.message else ''
                    problems.append(_job_line(job, '⚠️') + msg)
                elif failed:
                    counters[Status.WARNING] += 1
                    problems.append(_job_line(job, '⚠️') + f' — ошибок за период: {len(failed)}, '
                                                        f'последний отчёт успешный')
                else:
                    ok_count += 1
                    counters[Status.OK] += 1

        if not problems and not ok_count:
            continue
        title = f'🏢 <b>{escape(company.name)}</b>'
        if problems:
            tail = [f'  ✅ в норме: {ok_count}'] if ok_count else []
            blocks.append('\n'.join([title, *problems, *tail]))
        else:
            blocks.append(f'{title} — ✅ всё в норме ({ok_count})')

    header = (f'📊 <b>Сводка по бэкапам</b>\n'
              f'{_local(period_start)} — {_local(period_end)}\n'
              f'✅ {counters[Status.OK]}   ⚠️ {counters[Status.WARNING]}   '
              f'❌ {counters[Status.ERROR]}   ⏳ {counters[MISSING]}')
    body = '\n\n'.join(blocks) if blocks else 'Нет серверов на мониторинге.'
    return f'{header}\n\n{body}{dashboard_link()}', counters
