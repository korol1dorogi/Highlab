# shop/urls.py
from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    # Главная страница магазина - список товаров
    path('', views.ProductListView.as_view(), name='product_list'),
    
    # Товары по категории
    path('category/<slug:category_slug>/', 
         views.ProductListView.as_view(), 
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

     # Корзина
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('cart/update/<int:product_id>/', views.cart_update, name='cart_update'),
    path('cart/clear/', views.cart_clear, name='cart_clear'),
    path('checkout/', views.checkout, name='checkout'),
    path('order/success/<int:order_id>/', views.order_success, name='order_success'),
]