# shop/views.py
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import Q
from .models import Category, Product, Review
from django.contrib import messages
from django.http import JsonResponse
from .cart import CartManager
from .forms import OrderForm
from .models import Category, Product, ProductImage, Review, Cart, CartItem, Order, OrderItem
from .telegram_service import TelegramService
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

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
                Q(sku__icontains=search_query)
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
    

# shop/views.py
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
        return Product.objects.filter(available=True).prefetch_related('images', 'reviews')
    
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
    
# shop/views.py
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
    
# shop/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

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
        Q(sku__icontains=query),
        available=True
    )[:10]
    
    results = []
    for product in products:
        results.append({
            'name': product.name,
            'url': product.get_absolute_url(),
            'price': str(product.price),
            'image_url': product.main_image.url if product.main_image else None,
            'category': product.category.name
        })
    
    return JsonResponse({'results': results})


# shop/views.py - добавляем импорт
from .cart import CartManager
from django.contrib import messages

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
    """Добавление товара в корзину"""
    try:
        quantity = int(request.POST.get('quantity', 1))
        cart_manager = CartManager(request)
        success, message = cart_manager.add(product_id, quantity)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # AJAX запрос - возвращаем JSON
            return JsonResponse({
                'success': success,
                'message': message,
                'total_quantity': cart_manager.get_total_quantity(),
                'total_price': str(cart_manager.get_total_price())
            })
        else:
            # Обычный запрос - показываем сообщение и редиректим НАЗАД
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
def cart_update(request, product_id):
    """Обновление количества товара в корзине - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    print(f"DEBUG: cart_update called for product {product_id}")
    
    try:
        quantity = int(request.POST.get('quantity', 1))
        print(f"DEBUG: quantity = {quantity}")
        
        cart_manager = CartManager(request)
        
        if quantity <= 0:
            return cart_remove(request, product_id)
        
        # Используем метод update из CartManager
        success, message = cart_manager.update(product_id, quantity)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            item_total = '0'
            if success:
                try:
                    cart_item = CartItem.objects.get(
                        cart=cart_manager.cart,
                        product_id=product_id
                    )
                    item_total = str(cart_item.total_price)
                    print(f"DEBUG: item_total = {item_total}")
                except CartItem.DoesNotExist:
                    print("DEBUG: CartItem not found")
                    pass
            
            response_data = {
                'success': success,
                'message': message,
                'total_quantity': cart_manager.get_total_quantity(),
                'total_price': str(cart_manager.get_total_price()),
                'item_total': item_total
            }
            print(f"DEBUG: Response data = {response_data}")
            return JsonResponse(response_data)
        else:
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
            return redirect('shop:cart_detail')
            
    except Exception as e:
        print(f"DEBUG: Error in cart_update: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f'Ошибка: {str(e)}'
            })
        else:
            messages.error(request, f'Ошибка: {str(e)}')
            return redirect('shop:cart_detail')

@require_POST
def cart_remove(request, product_id):
    """Удаление товара из корзины"""
    try:
        cart_manager = CartManager(request)
        success, message = cart_manager.remove(product_id)
        
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
            
            # Создаем элементы заказа
            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.price
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
        return render(request, 'order_success.html', context)  # ⬅️ Добавляем 'shop/'
    except Order.DoesNotExist:
        messages.error(request, "Заказ не найден")
        return redirect('shop:product_list')