# create_test_data.py
import os
import django
from django.core.files import File

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from shop.models import Category, Product, ProductImage, Review
from django.contrib.auth.models import User

def create_test_data():
    # Создаем категории
    electronics = Category.objects.create(
        name='Электроника',
        slug='electronics',
        description='Современная электроника и гаджеты'
    )
    
    smartphones = Category.objects.create(
        name='Смартфоны',
        slug='smartphones',
        parent=electronics,
        description='Мобильные телефоны и смартфоны'
    )
    
    laptops = Category.objects.create(
        name='Ноутбуки',
        slug='laptops',
        parent=electronics,
        description='Портативные компьютеры'
    )
    
    # Создаем тестовые товары
    product1 = Product.objects.create(
        category=smartphones,
        name='iPhone 15 Pro',
        slug='iphone-15-pro',
        sku='APPLE-IP15P-256',
        description='Новый iPhone 15 Pro с революционной камерой и процессором A17 Pro.',
        price=99990,
        old_price=109990,
        quantity=10,
        available=True
    )
    
    product2 = Product.objects.create(
        category=smartphones,
        name='Samsung Galaxy S24',
        slug='samsung-galaxy-s24',
        sku='SAMSUNG-S24-256',
        description='Флагманский смартфон Samsung с искусственным интеллектом.',
        price=79990,
        quantity=5,
        available=True
    )
    
    product3 = Product.objects.create(
        category=laptops,
        name='MacBook Pro 16"',
        slug='macbook-pro-16',
        sku='APPLE-MBP16-1TB',
        description='Профессиональный ноутбук для творческих задач.',
        price=199990,
        old_price=219990,
        quantity=3,
        available=True
    )
    
    product4 = Product.objects.create(
        category=laptops,
        name='Dell XPS 13',
        slug='dell-xps-13',
        sku='DELL-XPS13-512',
        description='Ультрабук с безрамочным дисплеем.',
        price=89990,
        quantity=0,  # Нет в наличии
        available=False
    )
    
    print("Тестовые данные созданы!")
    print(f"Создано категорий: {Category.objects.count()}")
    print(f"Создано товаров: {Product.objects.count()}")

if __name__ == '__main__':
    create_test_data()