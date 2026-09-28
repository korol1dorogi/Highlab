# API мониторинга бэкапов

Сервера клиентов шлют отчёты на сайт → сводка на `/monitoring/` (только персонал),
мгновенные тревоги (❌ упало / ✅ восстановилось) и ежедневная сводка в Telegram.

## Подключение сервера

1. Админка → **Мониторинг бэкапов** → добавить компанию и сервер.
2. В карточке сервера — готовый `monitor.config.psd1` с токеном. Положить рядом с `VTMonitor.ps1`
   (или передать через `Initialize-VTMonitor` / переменные `VT_MONITOR_URL`, `VT_MONITOR_TOKEN`).
   Токен — пароль сервера.

## Клиент для PowerShell — `VTMonitor.ps1`

Windows PowerShell 5.1+, без модулей. Файл сохранён в UTF-8 **с BOM** — так и оставлять,
иначе PS 5.1 испортит кириллицу.

```powershell
. 'C:\VTMonitor\VTMonitor.ps1'

# 1. Один отчёт — в конце существующего скрипта
Send-VTReport -Job 'PG buh_main' -Status ok -Engine postgresql -Database buh_main `
    -Path $file -StartedAt $start -FinishedAt (Get-Date) -Message 'pg_dump OK'

# 2. Обёртка: время, исключения и $LASTEXITCODE → ok/error автоматически
Invoke-VTJob -Job 'PG buh_main' -Engine postgresql -Database buh_main -Path $file -ScriptBlock {
    & pg_dump.exe -Fc -f $file buh_main
}

# 3. Пакет — несколько баз одним запросом
$reports = foreach ($db in 'buh', 'zup', 'ut') {
    New-VTReport -Job "MSSQL $db" -Status ok -Engine mssql -Database $db -Path "E:\bak\$db.bak"
}
Send-VTReports -Reports $reports
```

| Функция | Назначение |
|---|---|
| `Send-VTReport` | Отправить один отчёт. |
| `New-VTReport` + `Send-VTReports` | Собрать несколько отчётов и отправить одним запросом (до 100). |
| `Invoke-VTJob` | Выполнить блок и сообщить результат. Вывод блока (stdout+stderr) идёт в сообщение, хвост до 3500 символов. Возвращает `$true`/`$false`. |
| `Initialize-VTMonitor` | Задать URL и токен из кода. |

- `-Path` на существующий файл — размер подставится сам.
- Сеть недоступна → 3 попытки, затем отчёт в `queue\`, досылается при следующей отправке.
  Ответ 4xx (токен/формат) не повторяется — пишется в лог и `Write-Warning`.
- Лог: `logs\vtmonitor.log` рядом с файлом.
- В `Invoke-VTJob` утилиты, пишущие прогресс в stderr (`pg_dump -v`), при `$ErrorActionPreference = 'Stop'`
  дадут ложную ошибку — в таких скриптах не включайте Stop или не используйте `-v`.

## HTTP API

`POST /monitoring/api/report/`
Заголовки: `Authorization: Bearer <токен>` (или `X-Monitor-Token: <токен>`), `Content-Type: application/json`.
Тело — UTF-8 JSON, до 512 КБ. Один отчёт или пакет:

```json
{
  "host": {"hostname": "SRV-1C", "os": "Windows Server 2019", "agent_version": "1.0"},
  "reports": [
    {
      "job": "PG buh_main",
      "status": "ok",
      "kind": "backup",
      "engine": "postgresql",
      "database": "buh_main",
      "started_at": "2026-09-29T02:00:00+03:00",
      "finished_at": "2026-09-29T02:14:31+03:00",
      "size_bytes": 5368709120,
      "path": "D:\\Backup\\buh_main_2026-09-29.backup",
      "message": "pg_dump OK",
      "expected_every_hours": 24,
      "details": {"free_disk_percent": 41.2}
    }
  ]
}
```

| Поле | Обяз. | Значения / смысл |
|---|---|---|
| `job` | да | Имя задания, уникально в пределах сервера, до 160 символов. Задание создаётся при первом отчёте, по имени копится история. Не включайте в имя дату. |
| `status` | да | `ok` · `warning` (сделано, но есть на что посмотреть) · `error` (копии нет / битая). |
| `kind` | | `backup` (по умолч.) · `health` (состояние сервера) · `check`. |
| `engine` | | `postgresql` · `mssql` · `1c` · `files` · `other`. |
| `database` | | Имя базы. |
| `started_at`, `finished_at` | | ISO 8601, лучше с часовым поясом; без пояса считается МСК. |
| `size_bytes` | | Целое. |
| `path` | | До 500 символов. |
| `message` | | Текст для людей, попадает в Telegram. До 4000 символов. |
| `expected_every_hours` | | Как часто ждать отчёт по заданию (по умолч. 24). Нет отчёта дольше + 2 ч → «⏳ нет отчёта» в сводке. |
| `details` | | Произвольный JSON-объект, виден на странице отчёта. |

`host` — необязательный, обновляет данные сервера в админке.

**Ответы:**
- `200 {"ok": true, "accepted": 2, "errors": []}` — принято. Если часть отчётов в пакете невалидна,
  они перечислены в `errors`, остальные сохранены.
- `400` — не JSON / ни одного валидного отчёта (`errors` объясняет).
- `401` — неверный или отключённый токен.
- `413` — тело больше 512 КБ.

**Когда шлётся Telegram:** сразу — при `error` и при `ok` после `error`; сводка — раз в сутки.

Проверка без PowerShell:
```bash
curl -X POST https://xn----7sbadh8ar0abscwf3p.xn--p1ai/monitoring/api/report/ \
  -H "Authorization: Bearer ТОКЕН" -H "Content-Type: application/json" \
  -d '{"job":"test","status":"ok","message":"проверка связи"}'
```

## Сервер сайта

Ежедневная сводка — cron на хосте (UTC; 05:00 UTC = 08:00 МСК):
```
0 5 * * * cd /root/Highlab && docker compose -f docker-compose.prod.yml exec -T web python manage.py send_monitoring_digest >> /root/logs/monitoring-digest.log 2>&1
```
`--dry-run` — напечатать сводку без отправки. Команда же чистит отчёты старше 180 дней (`MONITORING_RETENTION_DAYS`).
