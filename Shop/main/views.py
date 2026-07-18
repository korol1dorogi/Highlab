# shop/views.py
import logging

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404

logger = logging.getLogger(__name__)


def _can_access_order(request, order):
    """Право просмотра заказа.

    Разрешаем, если пользователь авторизован и это его заказ, ЛИБО если совпадает
    ключ сессии, оформившей заказ. Для гостевых заказов доступ по cookie сессии —
    это удобно, но небезопасно: при истечении/смене cookie доступ теряется, поэтому
    на странице успеха гостю рекомендуем сохранить PDF-квитанцию.
    """
    if request.user.is_authenticated and order.user_id and order.user_id == request.user.id:
        return True
    session_key = request.session.session_key
    if order.session_key and session_key and order.session_key == session_key:
        return True
    return False
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.urls import reverse
from django.db.models import Min, Max
from django.db.models.functions import Coalesce

from .models import Category, Product, ProductVariant, ProductImage, Review, Cart, CartItem, Order, OrderItem
from .cart import CartManager
from .forms import OrderForm
from .tasks import send_order_notification, send_order_confirmation

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
from datetime import datetime

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

def product_list(request, category_path=None):
    """
    Функциональное представление для списка товаров с фильтрацией и сортировкой
    """
    # Базовый queryset (prefetch вариантов — устраняем N+1 в свойствах min_price/in_stock)
    queryset = Product.objects.filter(available=True).select_related('category').prefetch_related('variants')
    
    # Обработка категории
    current_category = None
    breadcrumbs = [{'name': 'Все товары', 'url': reverse('shop:product_list')}]
    
    if category_path:
        path_parts = category_path.split('/')
        current_slug = path_parts[-1]
        current_category = get_object_or_404(Category, slug=current_slug)
        
        # Проверяем путь
        expected_path = '/'.join([cat.slug for cat in current_category.get_ancestors(include_self=True)])
        if expected_path != category_path:
            raise Http404("Категория не найдена")
        
        # Фильтруем товары
        categories = current_category.get_descendants(include_self=True)
        queryset = queryset.filter(category__in=categories)
        
        # Хлебные крошки
        breadcrumbs = current_category.get_breadcrumbs()
    
    # Поиск
    search_query = request.GET.get('search')
    if search_query and search_query != 'None':  # Фиксим проблему с "None"
        queryset = queryset.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(search_synonyms__icontains=search_query)
        )
    
    # ФИЛЬТРАЦИЯ ПО ЦЕНЕ - УПРОЩЕННАЯ РАБОЧАЯ ВЕРСИЯ
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    price_mode = request.GET.get('price_mode', 'strict')
    
    # Сначала аннотируем минимальную цену вариантов
    queryset = queryset.annotate(
        min_variant_price=Min('variants__price')
    )
    
    # Для фильтрации используем эффективную цену
    if min_price:
        try:
            min_price_val = float(min_price)
            if price_mode == 'smart':
                # УМНЫЙ РЕЖИМ: уменьшаем минимальную цену на 10%
                min_price_val = max(0, min_price_val * 0.9)  # Защита от отрицательных цен
            queryset = queryset.filter(base_price__gte=min_price_val)
        except (ValueError, TypeError):
            pass
    
    if max_price:
        try:
            max_price = float(max_price)
            if price_mode == 'smart':
                expanded_max = max_price * 1.1
                queryset = queryset.filter(
                    Q(min_variant_price__lte=expanded_max) | 
                    Q(min_variant_price__isnull=True, base_price__lte=expanded_max)
                )
            else:
                queryset = queryset.filter(
                    Q(min_variant_price__lte=max_price) | 
                    Q(min_variant_price__isnull=True, base_price__lte=max_price)
                )
        except (ValueError, TypeError):
            pass
    
    # СОРТИРОВКА - ИСПРАВЛЕННАЯ ВЕРСИЯ
    sort = request.GET.get('sort', 'default')
    
    if sort in ['price_asc', 'price_desc']:
        # Для сортировки по цене используем эффективную цену
        queryset = queryset.annotate(
            effective_price=Coalesce('min_variant_price', 'base_price')
        )
        if sort == 'price_asc':
            queryset = queryset.order_by('effective_price')
        else:
            queryset = queryset.order_by('-effective_price')
    else:
        sort_mapping = {
            'default': '-created',
            'name_asc': 'name',
            'name_desc': '-name',
            'popular': '-total_quantity',
        }
        order_by = sort_mapping.get(sort, '-created')
        queryset = queryset.order_by(order_by)
    
    # ПАГИНАЦИЯ
    from django.conf import settings
    paginate_by = getattr(settings, 'PRODUCTS_PER_PAGE', 12)
    paginator = Paginator(queryset, paginate_by)
    page_number = request.GET.get('page', 1)
    
    try:
        products = paginator.page(page_number)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    
    # Получаем диапазон цен для всех товаров (для отображения в форме)
    price_range = Product.objects.filter(available=True).annotate(
        effective_price=Coalesce(Min('variants__price'), 'base_price')
    ).aggregate(
        min_price=Min('effective_price'),
        max_price=Max('effective_price')
    )
    
    context = {
        'products': products,
        'categories': Category.get_root_categories(),
        'current_category': current_category,
        'breadcrumbs': breadcrumbs,
        'paginate_by': paginate_by,
        'price_range': price_range,
        'current_filters': {
            'min_price': min_price,
            'max_price': max_price,
            'price_mode': price_mode,
            'sort': sort,
            'search': search_query,
        },
    }

    return render(request, 'product_list.html', context)

class ProductDetailView(DetailView):
    """
    Представление для детальной страницы товара
    Особенности: изображения, отзывы, похожие товары
    """
    model = Product
    template_name = 'product_detail.html'
    context_object_name = 'product'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        return Product.objects.filter(available=True).prefetch_related('images', 'reviews', 'variants')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        
        # Похожие товары (из той же категории)
        context['related_products'] = Product.objects.filter(
            category=product.category,
            available=True
        ).exclude(id=product.id)[:4]
        
        # Одобренные отзывы + агрегат для микроразметки (звёзды в выдаче)
        from django.db.models import Avg
        approved = product.reviews.filter(is_approved=True)
        context['approved_reviews'] = approved
        context['review_count'] = approved.count()
        context['review_avg'] = approved.aggregate(avg=Avg('rating'))['avg']

        return context

class CategoryListView(ListView):
    """
    Представление для списка категорий с древовидной структурой
    """
    model = Category
    template_name = 'category_list.html'
    context_object_name = 'categories'
    
    def get_queryset(self):
        return Category.get_root_categories()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['featured_products'] = Product.objects.filter(
            available=True
        )[:8]
        return context

@login_required
@require_POST
def add_review(request, product_slug):
    """
    Представление для добавления отзыва
    Особенности: проверка авторизации, валидация
    """
    product = get_object_or_404(Product, slug=product_slug, available=True)

    # Валидация ввода: оценка 1..5 и непустой текст (иначе 500 / мусор в БД).
    try:
        rating = int(request.POST.get('rating', ''))
    except (TypeError, ValueError):
        rating = 0
    comment = request.POST.get('comment', '').strip()

    if rating < 1 or rating > 5:
        messages.error(request, 'Пожалуйста, выберите оценку от 1 до 5.')
        return redirect('shop:product_detail', slug=product_slug)
    if not comment:
        messages.error(request, 'Пожалуйста, напишите текст отзыва.')
        return redirect('shop:product_detail', slug=product_slug)

    # Проверяем, не оставлял ли пользователь уже отзыв
    if Review.objects.filter(product=product, user=request.user).exists():
        messages.error(request, 'Вы уже оставляли отзыв на этот товар')
        return redirect('shop:product_detail', slug=product_slug)

    # Создаём отзыв; на гонке двойной отправки ловим IntegrityError (unique_together)
    try:
        Review.objects.create(
            product=product,
            user=request.user,
            rating=rating,
            comment=comment,
            is_approved=False,  # Требует модерации
        )
    except IntegrityError:
        messages.error(request, 'Вы уже оставляли отзыв на этот товар')
        return redirect('shop:product_detail', slug=product_slug)

    messages.success(request, 'Ваш отзыв отправлен на модерацию')
    return redirect('shop:product_detail', slug=product_slug)

def product_search(request):
    """
    Представление для поиска товаров
    Особенности: AJAX-поиск, подсказки
    """
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({'results': []})
    
    products = Product.objects.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query) |
        Q(sku__icontains=query) |
        Q(search_synonyms__icontains=query),
        available=True
    )[:10]
    
    results = []
    for product in products:
        results.append({
            'name': product.name,
            'url': product.get_absolute_url(),
            'price': str(product.base_price),
            'image_url': product.main_image.url if product.main_image else None,
            'category': product.category.name
        })
    
    return JsonResponse({'results': results})

def cart_detail(request):
    """Страница корзины"""
    cart_manager = CartManager(request)
    cart_items = cart_manager.get_items()
    
    context = {
        'cart_items': cart_items,
        'total_price': cart_manager.get_total_price(),
        'total_quantity': cart_manager.get_total_quantity(),
    }
    return render(request, 'cart_detail.html', context)

@require_POST
def cart_add(request, product_id):
    """Добавление товара в корзину - ОБНОВЛЕННАЯ ВЕРСИЯ ДЛЯ ВАРИАНТОВ"""
    try:
        variant_id = request.POST.get('variant_id')  # Получаем ID варианта
        quantity = int(request.POST.get('quantity', 1))
        
        if not variant_id:
            return JsonResponse({
                'success': False,
                'message': 'Не выбран вариант товара'
            })
        
        cart_manager = CartManager(request)
        success, message = cart_manager.add(variant_id, quantity)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': success,
                'message': message,
                'total_quantity': cart_manager.get_total_quantity(),
                'total_price': str(cart_manager.get_total_price())
            })
        else:
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
            return redirect(request.META.get('HTTP_REFERER', 'shop:product_list'))
            
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f'Ошибка: {str(e)}'
            })
        else:
            messages.error(request, f'Ошибка: {str(e)}')
            return redirect('shop:product_list')

@require_POST
def cart_update(request, variant_id):
    """Обновление количества товара в корзине - ДЛЯ ВАРИАНТОВ"""
    try:
        action = request.POST.get('action')
        current_quantity = int(request.POST.get('current_quantity', 1))

        # Вычисляем новое количество на основе действия
        if action == 'increase':
            quantity = current_quantity + 1
        elif action == 'decrease':
            quantity = current_quantity - 1
        else:
            # Если действие не распознано, используем переданное количество
            quantity = int(request.POST.get('quantity', current_quantity))

        cart_manager = CartManager(request)

        if quantity <= 0:
            return cart_remove(request, variant_id)

        success, message = cart_manager.update(variant_id, quantity)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            item_total = '0'
            current_quantity = 0

            if success:
                try:
                    cart_item = CartItem.objects.get(
                        cart=cart_manager.cart,
                        product_variant_id=variant_id
                    )
                    item_total = str(cart_item.total_price)
                    current_quantity = cart_item.quantity
                except CartItem.DoesNotExist:
                    pass

            response_data = {
                'success': success,
                'message': message,
                'total_quantity': cart_manager.get_total_quantity(),
                'total_price': str(cart_manager.get_total_price()),
                'item_total': item_total,
                'current_quantity': current_quantity
            }

            return JsonResponse(response_data)
        else:
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
            return redirect('shop:cart_detail')
            
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f'Ошибка: {str(e)}'
            })
        else:
            messages.error(request, f'Ошибка: {str(e)}')
            return redirect('shop:cart_detail')


@require_POST
def cart_remove(request, variant_id):
    """Удаление товара из корзины - ДЛЯ ВАРИАНТОВ"""
    try:
        cart_manager = CartManager(request)
        success, message = cart_manager.remove(variant_id)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': success,
                'message': message,
                'total_quantity': cart_manager.get_total_quantity(),
                'total_price': str(cart_manager.get_total_price())
            })
        else:
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
            return redirect('shop:cart_detail')
            
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f'Ошибка: {str(e)}'
            })
        else:
            messages.error(request, f'Ошибка: {str(e)}')
            return redirect('shop:cart_detail')

@require_POST
def cart_clear(request):
    """Очистка корзины"""
    try:
        cart_manager = CartManager(request)
        cart_manager.cart.items.all().delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Корзина очищена',
                'total_quantity': 0,
                'total_price': '0'
            })
        else:
            messages.success(request, "Корзина очищена")
            return redirect('shop:cart_detail')
            
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f'Ошибка: {str(e)}'
            })
        else:
            messages.error(request, f'Ошибка: {str(e)}')
            return redirect('shop:cart_detail')

@never_cache
@csrf_protect
def checkout(request):
    """Страница оформления заказа - ДОСТУПНА БЕЗ АВТОРИЗАЦИИ"""
    cart_manager = CartManager(request)
    cart_items = cart_manager.get_items()
    
    if not cart_items:
        messages.error(request, "Ваша корзина пуста")
        return redirect('shop:cart_detail')
    
    total_price = cart_manager.get_total_price()
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            request.session['customer_data'] = {
                'first_name': form.cleaned_data['first_name'],
                'last_name': form.cleaned_data['last_name'],
                'email': form.cleaned_data['email'],
                'phone': form.cleaned_data['phone'],
            }

            # Для гостя ключ сессии нужен ДО транзакции: он может создать сессию.
            if not request.user.is_authenticated and not request.session.session_key:
                request.session.create()

            def queue_notifications(oid):
                """Ставим уведомления в очередь, но не роняем уже оформленный заказ,
                если брокер (Redis) недоступен."""
                try:
                    send_order_notification.delay(oid)
                    send_order_confirmation.delay(oid)
                except Exception:
                    logger.exception("Не удалось поставить в очередь уведомления по заказу #%s", oid)

            try:
                with transaction.atomic():
                    # Блокируем корзину: двойной клик / гонка не создадут дубль заказа.
                    cart = Cart.objects.select_for_update().get(pk=cart_manager.cart.pk)
                    items = list(
                        cart.items.select_related(
                            'product_variant', 'product_variant__product'
                        ).all()
                    )
                    if not items:
                        # Корзина уже очищена — значит заказ по этой отправке уже создан.
                        messages.info(request, "Похоже, этот заказ уже оформлен.")
                        return redirect('shop:cart_detail')

                    order = form.save(commit=False)
                    order.total_price = sum(item.total_price for item in items)
                    if request.user.is_authenticated:
                        order.user = request.user
                    order.session_key = request.session.session_key or ''
                    order.save()

                    OrderItem.objects.bulk_create([
                        OrderItem(
                            order=order,
                            product_variant=item.product_variant,
                            quantity=item.quantity,
                            price=item.price,
                        )
                        for item in items
                    ])

                    # Очищаем корзину в той же транзакции — атомарно с созданием заказа.
                    cart.items.all().delete()

                    # Уведомления — только после успешного коммита.
                    transaction.on_commit(lambda oid=order.id: queue_notifications(oid))
            except Exception:
                logger.exception("Ошибка при оформлении заказа")
                messages.error(
                    request,
                    "Не удалось оформить заказ. Попробуйте ещё раз или свяжитесь с нами."
                )
                return redirect('shop:checkout')

            messages.success(
                request,
                f"✅ Ваш заказ #{order.id} успешно оформлен! Мы свяжемся с вами в ближайшее время."
            )
            return redirect('shop:order_success', order_id=order.id)
    else:
        # Предзаполняем форму данными пользователя, если он авторизован
        initial_data = {}
        if request.user.is_authenticated:
            initial_data.update({
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
            })
            prof = getattr(request.user, 'profile', None)
            if prof and prof.phone:
                initial_data['phone'] = prof.display_phone
        customer_data = request.session.get('customer_data', {})
        if customer_data:
            initial_data.update(customer_data)

        form = OrderForm(initial=initial_data)
    
    context = {
        'form': form,
        'cart_items': cart_items,
        'total_price': total_price,
        'total_quantity': cart_manager.get_total_quantity(),
    }
    return render(request, 'checkout.html', context)

def order_success(request, order_id):
    """Страница успешного оформления заказа"""
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        messages.error(request, "Заказ не найден")
        return redirect('shop:product_list')

    # Проверка прав доступа: владелец заказа или сессия, оформившая заказ.
    if not _can_access_order(request, order):
        return HttpResponse("Доступ запрещен", status=403)

    # Гостю (доступ по cookie сессии) советуем сохранить PDF-квитанцию.
    guest_access = not (request.user.is_authenticated and order.user_id == request.user.id)
    context = {'order': order, 'guest_access': guest_access}
    return render(request, 'order_success.html', context)

def download_order_pdf(request, order_id):
    """Генерация PDF с русскими буквами используя системные шрифты"""
    order = get_object_or_404(Order, id=order_id)

    # Проверка прав доступа (тот же принцип, что и на странице успеха).
    if not _can_access_order(request, order):
        return HttpResponse("Доступ запрещен", status=403)

    # Реальные реквизиты компании из настроек сайта (а не заглушки).
    from index.models import SiteSettings, TeamContact
    site = SiteSettings.load()
    contact = TeamContact.objects.filter(is_active=True).first()
    company_name = site.company_name or 'Лаборатория ВТ'
    company_phone = contact.phone if contact and contact.phone else ''
    company_email = site.email or ''
    company_address = site.address or ''

    # Создаем буфер для PDF
    buffer = BytesIO()
    
    # Создаем PDF документ
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # АВТОМАТИЧЕСКИЙ ВЫБОР ШРИФТА С ПОДДЕРЖКОЙ КИРИЛЛИЦЫ
    # Пробуем найти системные шрифты с кириллицей
    font_name = "Helvetica"  # fallback
    
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import os
        
        # Список возможных путей к шрифтам с кириллицей
        font_paths = []
        
        if os.name == 'nt':  # Windows
            font_paths = [
                'C:/Windows/Fonts/arial.ttf',
                'C:/Windows/Fonts/tahoma.ttf',
                'C:/Windows/Fonts/verdana.ttf',
            ]
        else:  # Linux
            font_paths = [
                '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
            ]
        
        # Пробуем зарегистрировать первый доступный шрифт
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('CyrillicFont', font_path))
                    font_name = 'CyrillicFont'
                    print(f"Используем шрифт: {font_path}")
                    break
                except:
                    continue
                    
    except Exception as e:
        print(f"Не удалось зарегистрировать шрифт: {e}")
        # Используем стандартный Helvetica (без кириллицы)
    
    # Начальные координаты
    y_position = height - 50
    
    # Заголовок - увеличенный размер
    p.setFont(font_name, 18)
    p.drawString(50, y_position, company_name)
    y_position -= 35
    
    # Номер заказа
    p.setFont(font_name, 16)
    p.drawString(50, y_position, f"Заказ #{order.id}")
    y_position -= 25
    
    # Дата
    p.setFont(font_name, 10)
    p.drawString(50, y_position, f"Дата оформления: {order.created.strftime('%d.%m.%Y %H:%M')}")
    y_position -= 30
    
    # Разделитель
    p.line(50, y_position, width-50, y_position)
    y_position -= 30
    
    # Информация о покупателе
    p.setFont(font_name, 12)
    p.drawString(50, y_position, "Информация о покупателе:")
    y_position -= 20
    
    p.setFont(font_name, 10)
    p.drawString(50, y_position, f"Имя: {order.first_name} {order.last_name}")
    y_position -= 15
    p.drawString(50, y_position, f"Телефон: {order.phone}")
    y_position -= 15
    p.drawString(50, y_position, f"Email: {order.email}")
    y_position -= 15
    
    if order.address:
        # Адрес может быть длинным - разбиваем на строки
        address_lines = []
        words = order.address.split()
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if len(test_line) <= 50:
                current_line = test_line
            else:
                if current_line:
                    address_lines.append(current_line)
                current_line = word
        if current_line:
            address_lines.append(current_line)
        
        p.drawString(50, y_position, "Адрес:")
        y_position -= 15
        for line in address_lines:
            p.drawString(65, y_position, line)
            y_position -= 15
    else:
        y_position -= 15
    
    y_position -= 10
    
    # Разделитель
    p.line(50, y_position, width-50, y_position)
    y_position -= 20
    
    # Состав заказа
    p.setFont(font_name, 12)
    p.drawString(50, y_position, "Состав заказа:")
    y_position -= 25
    
    # Заголовки таблицы
    p.setFont(font_name, 10)
    p.drawString(50, y_position, "Товар")
    p.drawString(250, y_position, "Цена")
    p.drawString(320, y_position, "Кол-во")
    p.drawString(370, y_position, "Сумма")
    y_position -= 20
    
    # Линия под заголовком
    p.line(50, y_position, width-50, y_position)
    y_position -= 10
    
    p.setFont(font_name, 9)
    
    # Товары (ОБНОВЛЕНО ДЛЯ ВАРИАНТОВ)
    for item in order.items.all():
        if y_position < 100:
            p.showPage()
            y_position = height - 50
            p.setFont(font_name, 9)
        
        # Название товара с вариантом
        product_name = f"{item.product_variant.product.name} - {item.product_variant.name}"
        if len(product_name) > 45:
            product_name = product_name[:42] + "..."
        
        p.drawString(50, y_position, product_name)
        p.drawString(250, y_position, f"{item.price} ₽")
        p.drawString(320, y_position, str(item.quantity))
        p.drawString(370, y_position, f"{item.total_price} ₽")
        y_position -= 15
    
    y_position -= 10
    
    # Итоговая линия
    p.line(300, y_position, width-50, y_position)
    y_position -= 15
    
    # Итого
    p.setFont(font_name, 12)
    p.drawString(300, y_position, "Итого:")
    p.drawString(370, y_position, f"{order.total_price} ₽")
    y_position -= 30
    
    # Разделитель
    p.line(50, y_position, width-50, y_position)
    y_position -= 20
    
    # Подвал — реальные реквизиты компании
    p.setFont(font_name, 9)
    p.drawString(50, y_position, "Благодарим за ваш заказ!")
    y_position -= 15

    contacts_parts = [company_name]
    if company_phone:
        contacts_parts.append(f"Телефон: {company_phone}")
    p.drawString(50, y_position, " | ".join(contacts_parts))
    y_position -= 15
    if company_email:
        p.drawString(50, y_position, f"Email: {company_email}")
        y_position -= 15
    if company_address:
        p.drawString(50, y_position, f"Адрес: {company_address}")
        y_position -= 15
    p.drawString(50, y_position, f"Сформировано: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    
    # Сохраняем PDF
    p.showPage()
    p.save()
    
    # Получаем PDF из буфера
    pdf = buffer.getvalue()
    buffer.close()
    
    # Создаем HTTP response с PDF
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="order_{order.id}.pdf"'
    
    return response

def credits_view(request):
    return render(request, 'credits.html')