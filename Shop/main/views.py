# shop/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.db.models import Q
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
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
from .telegram_service import TelegramService

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from datetime import datetime

from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from .forms import SignUpForm, ProfileForm
# shop/views.py
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

def product_list(request, category_path=None):
    """
    Функциональное представление для списка товаров с фильтрацией и сортировкой
    """
    # Базовый queryset
    queryset = Product.objects.filter(available=True).select_related('category')
    
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
    paginate_by = 12
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
    
    # Отладочная информация
    debug_info = {
        'total_products': Product.objects.filter(available=True).count(),
        'filtered_products': queryset.count(),
        'min_price_param': min_price,
        'max_price_param': max_price,
        'sort_param': sort,
        'search_param': search_query,
    }
    debug_info = None
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
        'debug': debug_info
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
        
        # Одобренные отзывы
        context['approved_reviews'] = product.reviews.filter(is_approved=True)
        
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
    
    rating = request.POST.get('rating')
    comment = request.POST.get('comment', '').strip()
    
    # Проверяем, не оставлял ли пользователь уже отзыв
    existing_review = Review.objects.filter(product=product, user=request.user).first()
    if existing_review:
        messages.error(request, 'Вы уже оставляли отзыв на этот товар')
        return redirect('shop:product_detail', slug=product_slug)
    
    # Создаем отзыв
    review = Review.objects.create(
        product=product,
        user=request.user,
        rating=rating,
        comment=comment,
        is_approved=False  # Требует модерации
    )
    
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
    print(f"DEBUG cart_update: variant_id={variant_id}, POST data: {dict(request.POST)}")
    
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
        
        print(f"DEBUG cart_update: action={action}, current_quantity={current_quantity}, new_quantity={quantity}")
        
        cart_manager = CartManager(request)
        
        if quantity <= 0:
            return cart_remove(request, variant_id)
        
        success, message = cart_manager.update(variant_id, quantity)
        
        print(f"DEBUG cart_update: update result - success={success}, message={message}")
        
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
                    print(f"DEBUG cart_update: cart_item found - quantity={cart_item.quantity}, total_price={item_total}")
                except CartItem.DoesNotExist:
                    print("DEBUG cart_update: CartItem not found after update")
                    pass
            
            response_data = {
                'success': success,
                'message': message,
                'total_quantity': cart_manager.get_total_quantity(),
                'total_price': str(cart_manager.get_total_price()),
                'item_total': item_total,
                'current_quantity': current_quantity
            }
            
            print(f"DEBUG cart_update: response data = {response_data}")
            return JsonResponse(response_data)
        else:
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
            return redirect('shop:cart_detail')
            
    except Exception as e:
        print(f"DEBUG cart_update: Error - {str(e)}")
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
    cart_manager = CartManager(request)
    cart_items = cart_manager.get_items()

    if not cart_items:
        messages.error(request, "Ваша корзина пуста")
        return redirect('shop:cart_detail')

    total_price = cart_manager.get_total_price()

    if request.method == 'POST':
        form = OrderForm(request.POST, user=request.user)
        if form.is_valid():
            order = form.save(commit=False)
            order.total_price = total_price

            # Проверка постоплаты
            if order.payment_method == 'postpay':
                if not request.user.is_authenticated:
                    form.add_error('payment_method', 'Для постоплаты необходимо авторизоваться')
                else:
                    profile = request.user.profile
                    if not profile.postpay_available:
                        form.add_error('payment_method', 'Постоплата вам недоступна')
                    elif total_price > profile.available_postpay_limit:
                        form.add_error(
                            None,
                            f'Сумма заказа ({total_price} ₽) превышает доступный лимит постоплаты '
                            f'({profile.available_postpay_limit} ₽).'
                        )

            if form.errors:
                context = {
                    'form': form,
                    'cart_items': cart_items,
                    'total_price': total_price,
                    'total_quantity': cart_manager.get_total_quantity(),
                }
                return render(request, 'checkout.html', context)

            # Сохраняем заказ
            if request.user.is_authenticated:
                order.user = request.user
            else:
                order.session_key = request.session.session_key

            order.save()

            # Создаём элементы заказа
            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product_variant=cart_item.product_variant,
                    quantity=cart_item.quantity,
                    price=cart_item.price
                )

            # Если постоплата, резервируем сумму
            if order.payment_method == 'postpay' and request.user.is_authenticated:
                profile = request.user.profile
                profile.reserved_postpay += total_price
                profile.save(update_fields=['reserved_postpay'])
                order.status = 'processing_later'  # Сразу ставим статус ожидания постоплаты
                order.save(update_fields=['status'])

            # Отправка уведомления в Telegram
            telegram_service = TelegramService()
            telegram_service.send_order_notification(order)

            # Очищаем корзину
            cart_manager.clear()

            messages.success(request, f"✅ Ваш заказ #{order.id} успешно оформлен! Мы свяжемся с вами в ближайшее время.")
            return redirect('shop:order_success', order_id=order.id)
    else:
        initial_data = {}
        if request.user.is_authenticated:
            profile = request.user.profile
            initial_data = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
                'phone': profile.phone,
                'payment_method': 'postpay' if profile.postpay_available else 'online',
            }
        else:
            initial_data = request.session.get('customer_data', {})

        form = OrderForm(initial=initial_data, user=request.user)

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
        context = {'order': order}
        return render(request, 'order_success.html', context)
    except Order.DoesNotExist:
        messages.error(request, "Заказ не найден")
        return redirect('shop:product_list')

def download_order_pdf(request, order_id):
    """Генерация PDF с русскими буквами используя системные шрифты"""
    order = get_object_or_404(Order, id=order_id)
    
    # Проверка прав доступа
    if request.user.is_authenticated:
        if order.user != request.user:
            return HttpResponse("Доступ запрещен", status=403)
    else:
        if not hasattr(order, 'session_key') or order.session_key != request.session.session_key:
            return HttpResponse("Доступ запрещен", status=403)
    
    # Создаем буфер для PDF
    buffer = BytesIO()
    
    # Создаем PDF документ
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # АВТОМАТИЧЕСКИЙ ВЫБОР ШРИФТА С ПОДДЕРЖКОЙ КИРИЛЛИЦЫ
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
    p.drawString(50, y_position, "Highlab Store")
    y_position -= 35
    
    # Номер заказа
    p.setFont(font_name, 16)
    p.drawString(50, y_position, f"Заказ #{order.id}")
    y_position -= 25
    
    # Дата
    p.setFont(font_name, 10)
    created_date = order.created_at if hasattr(order, 'created_at') else order.created
    p.drawString(50, y_position, f"Дата оформления: {created_date.strftime('%d.%m.%Y %H:%M')}")
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
    
    # Подвал
    p.setFont(font_name, 9)
    p.drawString(50, y_position, "Благодарим за ваш заказ!")
    y_position -= 15
    p.drawString(50, y_position, "Highlab Store | Телефон: +7 (XXX) XXX-XX-XX")
    y_position -= 15
    p.drawString(50, y_position, "Email: info@highlab.ru")
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

def signup(request):
    """Регистрация нового пользователя"""
    if request.user.is_authenticated:
        return redirect('shop:profile')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно! Добро пожаловать!')
            return redirect('shop:profile')
    else:
        form = SignUpForm()
    
    return render(request, 'registration/signup.html', {'form': form})


def user_login(request):
    """Вход пользователя"""
    if request.user.is_authenticated:
        return redirect('shop:profile')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}!')
            next_url = request.GET.get('next', 'shop:profile')
            return redirect(next_url)
    else:
        form = AuthenticationForm()
    
    return render(request, 'registration/login.html', {'form': form})


def user_logout(request):
    """Выход пользователя"""
    logout(request)
    messages.info(request, 'Вы вышли из системы.')
    return redirect('shop:product_list')


@login_required
def profile(request):
    """Личный кабинет пользователя"""
    profile_instance = request.user.profile
    orders = request.user.main_orders.all().order_by('-created')[:10]
    context = {
        'profile': profile_instance,
        'orders': orders,
    }
    return render(request, 'profile/profile.html', context)


@login_required
def profile_edit(request):
    """Редактирование профиля"""
    profile_instance = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile_instance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлён.')
            return redirect('shop:profile')
    else:
        form = ProfileForm(instance=profile_instance)
    
    return render(request, 'profile/profile_edit.html', {'form': form})


@login_required
def change_password(request):
    """Смена пароля"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Пароль успешно изменён.')
            return redirect('shop:profile')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'profile/change_password.html', {'form': form})

def debug_products(request):
    """Временная функция для отладки"""
    products = Product.objects.filter(available=True)
    print(f"Всего товаров: {products.count()}")
    print(f"Paginate by: {12}")
    
    # Принудительно создаем пагинацию
    from django.core.paginator import Paginator
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    print(f"Всего страниц: {paginator.num_pages}")
    print(f"Текущая страница: {page_obj.number}")
    
    return render(request, 'product_list.html', {
        'products': page_obj,
        'categories': Category.get_root_categories(),
        'current_category': None,
        'breadcrumbs': [{'name': 'Все товары', 'url': reverse('shop:product_list')}],
        'paginate_by': 12
    })

def credits_view(request):
    return render(request, 'credits.html')