from django.conf import settings
from django.contrib import admin, messages
from django.utils.html import format_html

from .models import Job, MonitoredCompany, MonitoredHost, Report, generate_token


class HostInline(admin.TabularInline):
    model = MonitoredHost
    fields = ('name', 'hostname', 'last_seen_at', 'is_active')
    readonly_fields = ('hostname', 'last_seen_at')
    extra = 0
    show_change_link = True


@admin.register(MonitoredCompany)
class MonitoredCompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'hosts_count', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('name',)
    inlines = [HostInline]

    @admin.display(description='Серверов')
    def hosts_count(self, obj):
        return obj.hosts.count()


class JobInline(admin.TabularInline):
    model = Job
    fields = ('name', 'kind', 'engine', 'database', 'expected_every_hours', 'last_status', 'last_report_at', 'is_active')
    readonly_fields = ('last_status', 'last_report_at')
    extra = 0
    show_change_link = True


@admin.register(MonitoredHost)
class MonitoredHostAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'hostname', 'os_info', 'last_seen_at', 'is_active')
    list_filter = ('company', 'is_active')
    search_fields = ('name', 'hostname', 'company__name')
    readonly_fields = ('script_config', 'hostname', 'os_info', 'agent_version', 'last_seen_at', 'last_ip')
    fieldsets = (
        (None, {'fields': ('company', 'name', 'is_active', 'notes')}),
        ('Подключение скриптов', {'fields': ('script_config',)}),
        ('Сообщает сам сервер', {'fields': ('hostname', 'os_info', 'agent_version', 'last_seen_at', 'last_ip')}),
    )
    inlines = [JobInline]
    actions = ['regenerate_token']

    @admin.display(description='Файл monitor.config.psd1')
    def script_config(self, obj):
        if not obj.pk:
            return 'Сохраните сервер — здесь появится готовый конфиг с токеном.'
        url = getattr(settings, 'MONITORING_API_URL', '')
        config = (
            '@{\n'
            f"    ApiUrl = '{url}'\n"
            f"    Token  = '{obj.token}'\n"
            '}'
        )
        return format_html(
            '<pre style="user-select:all;margin:0">{}</pre>'
            '<div class="help">Сохраните как <code>monitor.config.psd1</code> рядом со скриптами '
            '(см. deploy/monitoring/README.md). Токен — это пароль сервера, не пересылайте его открыто.</div>',
            config,
        )

    @admin.action(description='Перевыпустить токен (старые скрипты перестанут работать)')
    def regenerate_token(self, request, queryset):
        for host in queryset:
            host.token = generate_token()
            host.save(update_fields=['token'])
        self.message_user(request, f'Токен перевыпущен для серверов: {queryset.count()}. '
                                   f'Обновите monitor.config.psd1 на этих серверах.', messages.WARNING)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('name', 'host', 'kind', 'engine', 'database', 'status_now', 'last_report_at',
                    'expected_every_hours', 'is_active')
    list_filter = ('host__company', 'kind', 'engine', 'last_status', 'is_active')
    list_editable = ('expected_every_hours', 'is_active')
    search_fields = ('name', 'database', 'host__name', 'host__company__name')
    readonly_fields = ('last_status', 'last_report_at', 'created')

    @admin.display(description='Сейчас')
    def status_now(self, obj):
        return f'{obj.status_icon} {obj.status_label}'


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('received_at', 'job', 'status', 'size_bytes', 'short_message')
    list_filter = ('status', 'job__host__company', 'job__kind')
    search_fields = ('message', 'job__name', 'job__host__name')
    date_hierarchy = 'received_at'
    list_select_related = ('job__host__company',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description='Сообщение')
    def short_message(self, obj):
        return (obj.message[:120] + '…') if len(obj.message) > 120 else obj.message
