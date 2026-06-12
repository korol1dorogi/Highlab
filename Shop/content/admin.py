from django.contrib import admin

from .models import Service, Project, Article, MediaItem, FAQItem


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'direction', 'icon_key', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    list_filter = ('direction', 'is_active')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'icon_key', 'direction', 'cover')}),
        ('Тексты', {'fields': ('description', 'body')}),
        ('Показ', {'fields': ('is_active', 'order')}),
    )


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'direction', 'published_at', 'is_published', 'order')
    list_editable = ('is_published', 'order')
    list_filter = ('direction', 'is_published')
    search_fields = ('title', 'summary', 'client')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'direction', 'summary', 'cover')}),
        ('Детали кейса', {'fields': ('client', 'sphere', 'task', 'solution', 'equipment', 'result')}),
        ('Публикация', {'fields': ('published_at', 'is_published', 'order')}),
    )


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'direction', 'published_at', 'is_published')
    list_editable = ('is_published',)
    list_filter = ('direction', 'is_published')
    search_fields = ('title', 'excerpt')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'direction', 'excerpt', 'cover')}),
        ('Содержание', {'fields': ('body',)}),
        ('Публикация', {'fields': ('published_at', 'is_published')}),
    )


@admin.register(MediaItem)
class MediaItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'kind', 'date', 'is_published', 'order')
    list_editable = ('is_published', 'order')
    list_filter = ('kind', 'is_published')
    search_fields = ('title', 'description')


@admin.register(FAQItem)
class FAQItemAdmin(admin.ModelAdmin):
    list_display = ('question', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    search_fields = ('question', 'answer')
