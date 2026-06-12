from django.contrib import admin

from .models import (
    SiteSettings, ServiceCard, CompanyStat, TeamContact, Advantage, Lead, Partner,
)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Главный экран', {'fields': ('company_name', 'hero_title', 'hero_subtitle')}),
        ('О компании', {'fields': ('about_title', 'about_text')}),
        ('Преимущества', {'fields': ('advantages_title',)}),
        ('Блок заявки', {'fields': ('lead_title', 'lead_subtitle')}),
        ('Контакты и соцсети', {
            'fields': ('address', 'email', 'vk_url', 'social_text', 'copyright_text')
        }),
        ('Аналитика', {'fields': ('metrika_id',)}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ServiceCard)
class ServiceCardAdmin(admin.ModelAdmin):
    list_display = ('title', 'icon_key', 'url', 'is_enabled', 'is_active', 'order')
    list_editable = ('is_enabled', 'is_active', 'order')
    list_filter = ('is_enabled', 'is_active')


@admin.register(CompanyStat)
class CompanyStatAdmin(admin.ModelAdmin):
    list_display = ('value', 'label', 'is_active', 'order')
    list_editable = ('is_active', 'order')


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    fields = ('name', 'logo', 'description', 'url', 'order', 'is_active')


@admin.register(TeamContact)
class TeamContactAdmin(admin.ModelAdmin):
    list_display = ('role_title', 'person_name', 'phone', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    list_filter = ('is_active',)


@admin.register(Advantage)
class AdvantageAdmin(admin.ModelAdmin):
    list_display = ('text', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    list_filter = ('is_active',)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'created', 'is_processed')
    list_editable = ('is_processed',)
    list_filter = ('is_processed', 'created')
    search_fields = ('name', 'phone', 'message')
    readonly_fields = ('created',)
