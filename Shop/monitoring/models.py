"""Мониторинг бэкапов и состояния серверов клиентов на обслуживании.

Сервера клиентов (Windows Server / Windows 10 с кластерами 1С, PostgreSQL, MS SQL)
по расписанию шлют PowerShell-скриптами отчёты на /monitoring/api/report/.
Каждый сервер авторизуется своим токеном. Отчёт относится к «заданию» (бэкап
конкретной базы, проверка состояния сервера и т.п.); задание создаётся
автоматически при первом отчёте. Если по заданию давно нет отчёта — оно
считается пропущенным и попадает в ежедневную сводку в Telegram.
"""
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_token():
    return secrets.token_urlsafe(32)


class Status(models.TextChoices):
    OK = 'ok', 'Норма'
    WARNING = 'warning', 'Предупреждение'
    ERROR = 'error', 'Ошибка'


# Вычисляемый статус задания, которое перестало присылать отчёты.
MISSING = 'missing'
STATUS_ICONS = {Status.OK: '✅', Status.WARNING: '⚠️', Status.ERROR: '❌', MISSING: '⏳'}
STATUS_LABELS = {**dict(Status.choices), MISSING: 'Нет отчёта'}


class MonitoredCompany(models.Model):
    name = models.CharField(max_length=160, unique=True, verbose_name='Компания')
    notes = models.TextField(blank=True, verbose_name='Заметки')
    is_active = models.BooleanField(default=True, verbose_name='На обслуживании')

    class Meta:
        verbose_name = 'Компания на обслуживании'
        verbose_name_plural = 'Компании на обслуживании'
        ordering = ['name']

    def __str__(self):
        return self.name


class MonitoredHost(models.Model):
    company = models.ForeignKey(MonitoredCompany, on_delete=models.CASCADE, related_name='hosts',
                                verbose_name='Компания')
    name = models.CharField(max_length=120, verbose_name='Сервер',
                            help_text='Как называть сервер в отчётах, напр. «SRV-1C»')
    token = models.CharField(max_length=64, unique=True, default=generate_token, editable=False,
                             verbose_name='Токен')
    hostname = models.CharField(max_length=120, blank=True, verbose_name='Имя компьютера',
                                help_text='Заполняется скриптом автоматически')
    os_info = models.CharField(max_length=200, blank=True, verbose_name='ОС')
    agent_version = models.CharField(max_length=40, blank=True, verbose_name='Версия скриптов')
    last_seen_at = models.DateTimeField(null=True, blank=True, verbose_name='Последний отчёт')
    last_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP последнего отчёта')
    notes = models.TextField(blank=True, verbose_name='Заметки')
    is_active = models.BooleanField(default=True, verbose_name='Отслеживать')

    class Meta:
        verbose_name = 'Сервер клиента'
        verbose_name_plural = 'Сервера клиентов'
        ordering = ['company__name', 'name']
        constraints = [
            models.UniqueConstraint(fields=['company', 'name'], name='monitoring_host_unique_name'),
        ]

    def __str__(self):
        return f'{self.company} / {self.name}'


class Job(models.Model):
    class Kind(models.TextChoices):
        BACKUP = 'backup', 'Резервная копия'
        HEALTH = 'health', 'Состояние сервера'
        CHECK = 'check', 'Проверка'

    class Engine(models.TextChoices):
        POSTGRESQL = 'postgresql', 'PostgreSQL'
        MSSQL = 'mssql', 'MS SQL'
        ONEC = '1c', '1С (выгрузка .dt)'
        FILES = 'files', 'Файлы'
        OTHER = 'other', 'Другое'

    host = models.ForeignKey(MonitoredHost, on_delete=models.CASCADE, related_name='jobs',
                             verbose_name='Сервер')
    name = models.CharField(max_length=160, verbose_name='Задание',
                            help_text='Уникально в пределах сервера, задаётся скриптом')
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.BACKUP, verbose_name='Тип')
    engine = models.CharField(max_length=12, choices=Engine.choices, blank=True, verbose_name='СУБД / источник')
    database = models.CharField(max_length=160, blank=True, verbose_name='База')
    expected_every_hours = models.PositiveIntegerField(
        default=24, verbose_name='Отчёт ожидается каждые, ч',
        help_text='Если отчёта нет дольше (плюс запас) — задание считается пропущенным')
    is_active = models.BooleanField(default=True, verbose_name='Отслеживать')
    last_status = models.CharField(max_length=10, choices=Status.choices, blank=True,
                                   verbose_name='Последний статус')
    last_report_at = models.DateTimeField(null=True, blank=True, verbose_name='Последний отчёт')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Создано')

    class Meta:
        verbose_name = 'Задание'
        verbose_name_plural = 'Задания (бэкапы и проверки)'
        ordering = ['host__company__name', 'host__name', 'name']
        constraints = [
            models.UniqueConstraint(fields=['host', 'name'], name='monitoring_job_unique_name'),
        ]

    def __str__(self):
        return f'{self.host} / {self.name}'

    @property
    def deadline(self):
        """Момент, после которого отсутствие нового отчёта считается пропуском."""
        base = self.last_report_at or self.created
        grace = getattr(settings, 'MONITORING_GRACE_HOURS', 2)
        return base + timedelta(hours=self.expected_every_hours + grace)

    def current_status(self, now=None):
        if now is None:
            now = timezone.now()
        if self.deadline < now:
            return MISSING
        return self.last_status or MISSING

    @property
    def status_icon(self):
        return STATUS_ICONS[self.current_status()]

    @property
    def status_label(self):
        return STATUS_LABELS[self.current_status()]


class Report(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='reports', verbose_name='Задание')
    received_at = models.DateTimeField(default=timezone.now, db_index=True, verbose_name='Получен')
    status = models.CharField(max_length=10, choices=Status.choices, verbose_name='Статус')
    message = models.TextField(blank=True, verbose_name='Сообщение')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='Начало')
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name='Окончание')
    size_bytes = models.BigIntegerField(null=True, blank=True, verbose_name='Размер, байт')
    path = models.CharField(max_length=500, blank=True, verbose_name='Файл / путь')
    details = models.JSONField(default=dict, blank=True, verbose_name='Подробности')

    class Meta:
        verbose_name = 'Отчёт'
        verbose_name_plural = 'Отчёты'
        ordering = ['-received_at']

    def __str__(self):
        return f'{self.job} — {self.get_status_display()} ({self.received_at:%d.%m.%Y %H:%M})'

    @property
    def status_icon(self):
        return STATUS_ICONS[self.status]

    @property
    def duration(self):
        if self.started_at and self.finished_at and self.finished_at >= self.started_at:
            return self.finished_at - self.started_at
        return None
