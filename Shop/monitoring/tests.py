import json
from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import MISSING, Job, MonitoredCompany, MonitoredHost, Report, Status
from .services import build_digest, split_message

API = '/monitoring/api/report/'


@override_settings(TELEGRAM_BOT_TOKEN='', MONITORING_INSTANT_ALERTS=True, SECURE_SSL_REDIRECT=False)
class ApiTests(TestCase):
    def setUp(self):
        self.company = MonitoredCompany.objects.create(name='ООО Ромашка')
        self.host = MonitoredHost.objects.create(company=self.company, name='SRV-1C')

    def post(self, payload, token=None):
        return self.client.post(API, data=json.dumps(payload), content_type='application/json',
                                HTTP_AUTHORIZATION=f'Bearer {token or self.host.token}')

    def test_bad_token_rejected(self):
        resp = self.post({'job': 'x', 'status': 'ok'}, token='nope')
        self.assertEqual(resp.status_code, 401)
        self.assertFalse(Report.objects.exists())

    def test_inactive_host_rejected(self):
        self.host.is_active = False
        self.host.save()
        self.assertEqual(self.post({'job': 'x', 'status': 'ok'}).status_code, 401)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(API).status_code, 405)

    def test_single_report_creates_job(self):
        resp = self.post({
            'job': 'PG buh', 'status': 'ok', 'engine': 'postgresql', 'database': 'buh',
            'size_bytes': 1048576, 'started_at': '2026-09-29T02:00:00+03:00',
            'finished_at': '2026-09-29T02:05:00+03:00', 'expected_every_hours': 12,
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        job = Job.objects.get()
        self.assertEqual((job.engine, job.database, job.expected_every_hours, job.last_status),
                         ('postgresql', 'buh', 12, 'ok'))
        self.assertEqual(Report.objects.get().duration, timedelta(minutes=5))
        self.host.refresh_from_db()
        self.assertIsNotNone(self.host.last_seen_at)

    def test_batch_with_host_info_and_partial_errors(self):
        resp = self.post({
            'host': {'hostname': 'SRV1C', 'os': 'Windows Server 2019', 'agent_version': '1.0'},
            'reports': [
                {'job': 'health', 'kind': 'health', 'status': 'warning', 'details': {'disks': [{'C': 7}]}},
                {'job': 'broken', 'status': 'maybe'},
            ],
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['accepted'], 1)
        self.assertEqual(len(data['errors']), 1)
        self.host.refresh_from_db()
        self.assertEqual(self.host.os_info, 'Windows Server 2019')

    def test_invalid_json(self):
        resp = self.client.post(API, data='not json', content_type='application/json',
                                HTTP_AUTHORIZATION=f'Bearer {self.host.token}')
        self.assertEqual(resp.status_code, 400)

    def test_utf8_bom_accepted(self):
        body = '﻿' + json.dumps({'job': 'Выгрузка 1С', 'status': 'ok'}, ensure_ascii=False)
        resp = self.client.post(API, data=body.encode('utf-8'), content_type='application/json',
                                HTTP_X_MONITOR_TOKEN=self.host.token)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(Job.objects.get().name, 'Выгрузка 1С')

    def test_error_and_recovery_trigger_alerts(self):
        with mock.patch('monitoring.tasks.send_report_alert.delay') as delay:
            with self.captureOnCommitCallbacks(execute=True):
                self.post({'job': 'MSSQL', 'status': 'ok'})
            delay.assert_not_called()
            with self.captureOnCommitCallbacks(execute=True):
                self.post({'job': 'MSSQL', 'status': 'error', 'message': 'нет места'})
            self.assertEqual(delay.call_count, 1)
            with self.captureOnCommitCallbacks(execute=True):
                self.post({'job': 'MSSQL', 'status': 'ok'})
            self.assertEqual(delay.call_count, 2)


@override_settings(SECURE_SSL_REDIRECT=False, MONITORING_GRACE_HOURS=2)
class DigestAndPageTests(TestCase):
    def setUp(self):
        company = MonitoredCompany.objects.create(name='ООО <Ромашка>')
        self.host = MonitoredHost.objects.create(company=company, name='SRV', last_seen_at=timezone.now())
        now = timezone.now()
        self.ok = Job.objects.create(host=self.host, name='ok job', last_status='ok', last_report_at=now)
        Report.objects.create(job=self.ok, status='ok', received_at=now)
        self.err = Job.objects.create(host=self.host, name='err job', last_status='error', last_report_at=now)
        Report.objects.create(job=self.err, status='error', message='disk full', received_at=now)
        self.old = Job.objects.create(host=self.host, name='stale job', last_status='ok',
                                      last_report_at=now - timedelta(hours=30))

    def test_missing_status(self):
        self.assertEqual(self.old.current_status(), MISSING)
        self.assertEqual(self.ok.current_status(), Status.OK)

    def test_digest_counts_and_escaping(self):
        text, counters = build_digest()
        self.assertEqual(counters[Status.OK], 1)
        self.assertEqual(counters[Status.ERROR], 1)
        self.assertEqual(counters[MISSING], 1)
        self.assertIn('&lt;Ромашка&gt;', text)
        self.assertIn('disk full', text)

    def test_dashboard_staff_only(self):
        url = reverse('monitoring:dashboard')
        self.assertEqual(self.client.get(url).status_code, 302)
        user = User.objects.create_user('staff', password='x', is_staff=True)
        self.client.force_login(user)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'stale job')
        self.assertEqual(self.client.get(reverse('monitoring:job_detail', args=[self.err.pk])).status_code, 200)


class SplitTests(TestCase):
    def test_split_respects_limit(self):
        text = '\n'.join(['строка ' * 20] * 100)
        parts = split_message(text, limit=500)
        self.assertTrue(all(len(p) <= 500 for p in parts))
        self.assertEqual(''.join(parts).replace('\n', ''), text.replace('\n', ''))
