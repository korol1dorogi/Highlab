from django.shortcuts import render, get_object_or_404

from .models import Service, Project, Article, MediaItem, FAQItem, DIRECTION_CHOICES


def hub(request):
    """Главная страница /service/ — услуги и витрина экспертизы."""
    context = {
        'services': Service.objects.filter(is_active=True),
        'projects': Project.objects.filter(is_published=True)[:3],
        'articles': Article.objects.filter(is_published=True)[:3],
        'media_items': MediaItem.objects.filter(is_published=True)[:4],
        'faqs': FAQItem.objects.filter(is_active=True),
    }
    return render(request, 'content/hub.html', context)


def service_detail(request, slug):
    """Отдельная страница услуги: описание + кейсы по направлению + CTA."""
    service = get_object_or_404(Service, slug=slug, is_active=True)
    related_projects = Project.objects.filter(
        is_published=True, direction=service.direction
    )[:3]
    related_articles = Article.objects.filter(
        is_published=True, direction=service.direction
    )[:3]
    other_services = Service.objects.filter(is_active=True).exclude(id=service.id)
    context = {
        'service': service,
        'related_projects': related_projects,
        'related_articles': related_articles,
        'other_services': other_services,
    }
    return render(request, 'content/service_detail.html', context)


def project_list(request):
    qs = Project.objects.filter(is_published=True)
    active = request.GET.get('direction')
    if active:
        qs = qs.filter(direction=active)
    context = {
        'projects': qs,
        'directions': DIRECTION_CHOICES,
        'active_direction': active,
    }
    return render(request, 'content/project_list.html', context)


def project_detail(request, slug):
    project = get_object_or_404(Project, slug=slug, is_published=True)
    related = Project.objects.filter(
        is_published=True, direction=project.direction
    ).exclude(id=project.id)[:3]
    return render(request, 'content/project_detail.html', {'project': project, 'related': related})


def article_list(request):
    qs = Article.objects.filter(is_published=True)
    active = request.GET.get('direction')
    if active:
        qs = qs.filter(direction=active)
    context = {
        'articles': qs,
        'directions': DIRECTION_CHOICES,
        'active_direction': active,
    }
    return render(request, 'content/article_list.html', context)


def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug, is_published=True)
    related = Article.objects.filter(
        is_published=True, direction=article.direction
    ).exclude(id=article.id)[:3]
    return render(request, 'content/article_detail.html', {'article': article, 'related': related})


def media_list(request):
    context = {
        'media_items': MediaItem.objects.filter(is_published=True),
        'kinds': MediaItem.KIND_CHOICES,
    }
    return render(request, 'content/media_list.html', context)
