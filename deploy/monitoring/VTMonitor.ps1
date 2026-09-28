# Клиент API мониторинга бэкапов «Лаборатория ВТ».
# Windows PowerShell 5.1+, без внешних модулей. Подключение в свой скрипт:
#
#   . 'C:\VTMonitor\VTMonitor.ps1'
#   Send-VTReport -Job 'PG buh_main' -Status ok -Engine postgresql -Database buh_main -Path $file
#
# Настройки (первое найденное):
#   1) Initialize-VTMonitor -ApiUrl ... -Token ...
#   2) переменные окружения VT_MONITOR_URL / VT_MONITOR_TOKEN
#   3) monitor.config.psd1 рядом с этим файлом (готовый конфиг — в админке, карточка сервера):
#        @{ ApiUrl = 'https://xn----7sbadh8ar0abscwf3p.xn--p1ai/monitoring/api/report/'; Token = '...' }
#
# Если сайт недоступен, отчёт кладётся в queue\ рядом с файлом и досылается при следующей отправке.

$script:VTMonitorVersion = '1.0'
$script:VTMonitorDir = $PSScriptRoot
$script:VTMonitorConfig = $null

function Initialize-VTMonitor {
    param([Parameter(Mandatory)][string]$ApiUrl, [Parameter(Mandatory)][string]$Token)
    $script:VTMonitorConfig = @{ ApiUrl = $ApiUrl; Token = $Token }
}

function Get-VTMonitorConfig {
    if ($script:VTMonitorConfig) { return $script:VTMonitorConfig }
    if ($env:VT_MONITOR_URL -and $env:VT_MONITOR_TOKEN) {
        return @{ ApiUrl = $env:VT_MONITOR_URL; Token = $env:VT_MONITOR_TOKEN }
    }
    $path = Join-Path $script:VTMonitorDir 'monitor.config.psd1'
    if (Test-Path $path) {
        $cfg = Import-PowerShellDataFile -Path $path
        if ($cfg.ApiUrl -and $cfg.Token) { $script:VTMonitorConfig = $cfg; return $cfg }
    }
    throw 'VTMonitor не настроен: вызовите Initialize-VTMonitor, задайте VT_MONITOR_URL/VT_MONITOR_TOKEN или положите monitor.config.psd1'
}

function Write-VTMonitorLog {
    param([string]$Message)
    $dir = Join-Path $script:VTMonitorDir 'logs'
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $file = Join-Path $dir 'vtmonitor.log'
    Add-Content -Path $file -Value ('{0:yyyy-MM-dd HH:mm:ss}  {1}' -f (Get-Date), $Message) -Encoding UTF8
    if ((Get-Item $file).Length -gt 5MB) { Move-Item $file "$file.old" -Force }
}

function New-VTReport {
    <#
    Собирает отчёт (hashtable) для Send-VTReports. Поля — см. README.md.
    Обязательны только Job и Status.
    #>
    param(
        [Parameter(Mandatory)][string]$Job,
        [Parameter(Mandatory)][ValidateSet('ok', 'warning', 'error')][string]$Status,
        [ValidateSet('backup', 'health', 'check')][string]$Kind = 'backup',
        [ValidateSet('', 'postgresql', 'mssql', '1c', 'files', 'other')][string]$Engine = '',
        [string]$Database = '',
        [string]$Message = '',
        # Путь к файлу копии; если SizeBytes не задан, размер файла подставится сам.
        [string]$Path = '',
        [Nullable[long]]$SizeBytes = $null,
        [Nullable[datetime]]$StartedAt = $null,
        [Nullable[datetime]]$FinishedAt = $null,
        [int]$ExpectedEveryHours = 0,
        [hashtable]$Details = @{}
    )
    if ($SizeBytes -eq $null -and $Path -and (Test-Path -LiteralPath $Path -PathType Leaf)) {
        $SizeBytes = (Get-Item -LiteralPath $Path).Length
    }
    $r = [ordered]@{ job = $Job; status = $Status; kind = $Kind }
    if ($Engine) { $r.engine = $Engine }
    if ($Database) { $r.database = $Database }
    if ($Message) { $r.message = $Message.Trim() }
    if ($Path) { $r.path = $Path }
    if ($SizeBytes -ne $null) { $r.size_bytes = $SizeBytes }
    # PowerShell сам разворачивает Nullable[datetime], поэтому приводим явно, без .Value
    if ($StartedAt) { $r.started_at = ([datetime]$StartedAt).ToString('yyyy-MM-ddTHH:mm:sszzz') }
    if ($FinishedAt) { $r.finished_at = ([datetime]$FinishedAt).ToString('yyyy-MM-ddTHH:mm:sszzz') }
    if ($ExpectedEveryHours -gt 0) { $r.expected_every_hours = $ExpectedEveryHours }
    if ($Details.Count) { $r.details = $Details }
    return $r
}

function Invoke-VTMonitorPost {
    param([string]$Json, $Config)
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $bytes = [Text.Encoding]::UTF8.GetBytes($Json)  # PS 5.1 без этого портит кириллицу
    Invoke-RestMethod -Uri $Config.ApiUrl -Method Post -UseBasicParsing -TimeoutSec 30 `
        -Headers @{ Authorization = "Bearer $($Config.Token)" } `
        -ContentType 'application/json; charset=utf-8' -Body $bytes
}

function Get-VTHttpCode($ErrorRecord) {
    if ($ErrorRecord.Exception.Response) { return [int]$ErrorRecord.Exception.Response.StatusCode }
    return 0
}

function Send-VTQueue {
    <# Досылает отчёты, отложенные из-за недоступности сайта. #>
    param($Config = (Get-VTMonitorConfig))
    $queue = Join-Path $script:VTMonitorDir 'queue'
    if (-not (Test-Path $queue)) { return }
    foreach ($f in Get-ChildItem $queue -Filter '*.json' | Sort-Object Name) {
        try {
            Invoke-VTMonitorPost -Json ([IO.File]::ReadAllText($f.FullName, [Text.Encoding]::UTF8)) -Config $Config | Out-Null
            Remove-Item $f.FullName -Force
            Write-VTMonitorLog "Дослан отложенный отчёт $($f.Name)"
        } catch {
            $code = Get-VTHttpCode $_
            if ($code -ge 400 -and $code -lt 500) { Move-Item $f.FullName "$($f.FullName).rejected" -Force; continue }
            break  # сайт всё ещё недоступен
        }
    }
}

function Send-VTReports {
    <#
    Отправляет пакет отчётов одним запросом (до 100 штук).
    Возвращает ответ сервера ({ok, accepted, errors}) или $null, если отчёт ушёл в очередь / отклонён.
    #>
    param([Parameter(Mandatory)][object[]]$Reports)
    $cfg = Get-VTMonitorConfig
    Send-VTQueue -Config $cfg

    $os = (Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue).Caption
    $payload = [ordered]@{
        host = [ordered]@{ hostname = $env:COMPUTERNAME; os = "$os"; agent_version = $script:VTMonitorVersion }
        reports = @($Reports)
    }
    $json = ConvertTo-Json -InputObject $payload -Depth 10 -Compress

    for ($i = 1; $i -le 3; $i++) {
        try {
            $resp = Invoke-VTMonitorPost -Json $json -Config $cfg
            Write-VTMonitorLog ("Принято отчётов: {0}{1}" -f $resp.accepted, $(if ($resp.errors) { '; ошибки: ' + ($resp.errors -join '; ') }))
            return $resp
        } catch {
            $code = Get-VTHttpCode $_
            Write-VTMonitorLog "Попытка $i не удалась (HTTP $code): $($_.Exception.Message)"
            if ($code -ge 400 -and $code -lt 500) {
                Write-Warning "VTMonitor: сервер отклонил отчёт (HTTP $code) — проверьте токен и поля"
                return $null
            }
            if ($i -lt 3) { Start-Sleep -Seconds (10 * $i) }
        }
    }

    $queue = Join-Path $script:VTMonitorDir 'queue'
    if (-not (Test-Path $queue)) { New-Item -ItemType Directory -Path $queue -Force | Out-Null }
    $file = Join-Path $queue ('{0:yyyyMMdd-HHmmss}-{1}.json' -f (Get-Date), (Get-Random))
    [IO.File]::WriteAllText($file, $json, (New-Object Text.UTF8Encoding $false))
    Write-VTMonitorLog "Сайт недоступен — отчёт отложен в $file"
    return $null
}

function Send-VTReport {
    <#
    Отправить один отчёт. Параметры — как у New-VTReport.
    Пример: Send-VTReport -Job 'MSSQL ZUP' -Status error -Engine mssql -Message $err
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Job,
        [Parameter(Mandatory)][ValidateSet('ok', 'warning', 'error')][string]$Status,
        [ValidateSet('backup', 'health', 'check')][string]$Kind = 'backup',
        [ValidateSet('', 'postgresql', 'mssql', '1c', 'files', 'other')][string]$Engine = '',
        [string]$Database = '',
        [string]$Message = '',
        [string]$Path = '',
        [Nullable[long]]$SizeBytes = $null,
        [Nullable[datetime]]$StartedAt = $null,
        [Nullable[datetime]]$FinishedAt = $null,
        [int]$ExpectedEveryHours = 0,
        [hashtable]$Details = @{}
    )
    Send-VTReports -Reports @(New-VTReport @PSBoundParameters)
}

function Invoke-VTJob {
    <#
    Обёртка над шагом бэкапа: засекает время, ловит исключения и ненулевой $LASTEXITCODE
    и сам отправляет ok/error. Если блок вернул строку — она станет сообщением отчёта.
    Возвращает $true, если шаг прошёл успешно.

    Пример:
      Invoke-VTJob -Job 'PG buh_main' -Engine postgresql -Database buh_main -Path $file -ScriptBlock {
          & pg_dump.exe -Fc -f $file buh_main
      }
    #>
    param(
        [Parameter(Mandatory)][string]$Job,
        [Parameter(Mandatory)][scriptblock]$ScriptBlock,
        [ValidateSet('backup', 'health', 'check')][string]$Kind = 'backup',
        [ValidateSet('', 'postgresql', 'mssql', '1c', 'files', 'other')][string]$Engine = '',
        [string]$Database = '',
        [string]$Path = '',
        [int]$ExpectedEveryHours = 0,
        [hashtable]$Details = @{}
    )
    $started = Get-Date
    $global:LASTEXITCODE = 0
    try {
        $output = & $ScriptBlock 2>&1
        $exit = $global:LASTEXITCODE
        $text = ($output | Out-String).Trim()
        if ($exit -ne 0) { $status = 'error'; $text = "Код возврата $exit`n$text" } else { $status = 'ok' }
    } catch {
        $status = 'error'
        $text = $_.Exception.Message
    }
    if ($text.Length -gt 3500) { $text = '…' + $text.Substring($text.Length - 3500) }  # хвост лога важнее

    Send-VTReport -Job $Job -Status $status -Kind $Kind -Engine $Engine -Database $Database -Message $text `
        -Path $Path -StartedAt $started -FinishedAt (Get-Date) -ExpectedEveryHours $ExpectedEveryHours `
        -Details $Details | Out-Null
    return ($status -eq 'ok')
}
