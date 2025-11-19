# shop/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.db.models import Q
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

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

class ProductListView(ListView):
    """
    Представление для списка товаров
    Особенности: пагинация, фильтрация по категориям, поиск
    """
    model = Product
    template_name = 'product_list.html'
    context_object_name = 'products'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Product.objects.filter(available=True).select_related('category')
        
        # Фильтрация по категории
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            queryset = queryset.filter(category=category)
        
        # Поиск
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(sku__icontains=search_query) |
                Q(search_synonyms__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(is_active=True)
        
        # Передаем текущую категорию в контекст
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            context['current_category'] = get_object_or_404(Category, slug=category_slug)
        
        return context

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
    Представление для списка категорий
    Особенности: древовидная структура, количество товаров
    """
    model = Category
    template_name = 'category_list.html'
    context_object_name = 'categories'
    
    def get_queryset(self):
        return Category.objects.filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Добавляем популярные товары для главной страницы категорий
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
            # Создаем заказ
            order = form.save(commit=False)
            order.total_price = total_price
            
            # Для авторизованных пользователей сохраняем связь
            if request.user.is_authenticated:
                order.user = request.user
            else:
                # Для анонимных пользователей сохраняем сессию
                order.session_key = request.session.session_key
            
            order.save()
            
            # Создаем элементы заказа (ОБНОВЛЕНО ДЛЯ ВАРИАНТОВ)
            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product_variant=cart_item.product_variant,  # Используем вариант товара
                    quantity=cart_item.quantity,
                    price=cart_item.price  # Используем цену из корзины
                )
            
            # Отправляем уведомление в Telegram
            telegram_service = TelegramService()
            telegram_service.send_order_notification(order)
            
            # Очищаем корзину
            cart_manager.clear()
            
            # Показываем сообщение об успехе
            messages.success(request, f"✅ Ваш заказ #{order.id} успешно оформлен! Мы свяжемся с вами в ближайшее время.")
            
            return redirect('shop:order_success', order_id=order.id)
    else:
        # Предзаполняем форму данными пользователя, если он авторизован
        initial_data = {}
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