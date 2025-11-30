# shop/urls.py
from django.urls import path, re_path
from . import views

app_name = 'shop'

urlpatterns = [
    # Главная страница магазина - список товаров
    path('', views.product_list, name='product_list'),  # ИЗМЕНЕНО
    
    # Товары по иерархической категории
    re_path(r'^category/(?P<category_path>[\w\/-]+)/$', 
            views.product_list,  # ИЗМЕНЕНО
            name='product_list_by_category'),
    
    # Детальная страница товара
    path('product/<slug:slug>/', 
         views.ProductDetailView.as_view(), 
         name='product_detail'),
    
    # Список категорий
    path('categories/', 
         views.CategoryListView.as_view(), 
         name='category_list'),
    
    # Добавление отзыва
    path('product/<slug:product_slug>/review/', 
         views.add_review, 
         name='add_review'),
    
    # Поиск товаров (API)
    path('search/', 
         views.product_search, 
         name='product_search'),

    # Корзина (ОБНОВЛЕННЫЕ URL ДЛЯ ВАРИАНТОВ)
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),  # product_id в URL, variant_id в POST
    path('cart/update/<int:variant_id>/', views.cart_update, name='cart_update'),  # variant_id в URL
    path('cart/remove/<int:variant_id>/', views.cart_remove, name='cart_remove'),  # variant_id в URL
    path('cart/clear/', views.cart_clear, name='cart_clear'),
    
    # Оформление заказа
    path('checkout/', views.checkout, name='checkout'),
    path('order/success/<int:order_id>/', views.order_success, name='order_success'),
    path('order/pdf/<int:order_id>/', views.download_order_pdf, name='download_order_pdf'),

    path('credits/', views.credits_view, name='credits'),

    # path('debug/', views.debug_products, name='debug_products'),
]