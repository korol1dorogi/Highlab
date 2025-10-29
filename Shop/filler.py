# filler.py (в корне проекта)
import os
import django
import sys

# Добавляем корневую директорию в Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настраиваем Django
#os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Shop.settings')
#django.setup()

from main.models import Category, Product
from django.contrib.auth.models import User

def fill_database():
    """Функция для наполнения базы данных"""
    print("Creating test data...")

    # Очищаем старые данные (осторожно!)
    # Product.objects.all().delete()
    # Category.objects.all().delete()

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

    # Создаем несколько товаров
    products = [
        {
            'category': smartphones,
            'name': 'iPhone 15 Pro',
            'slug': 'iphone-15-pro',
            'sku': 'APPLE-IP15P-256',
            'description': 'Новый iPhone 15 Pro',
            'price': 99990,
            'old_price': 109990,
            'quantity': 10,
        },
        {
            'category': smartphones, 
            'name': 'Samsung Galaxy S24',
            'slug': 'samsung-galaxy-s24',
            'sku': 'SAMSUNG-S24-256',
            'description': 'Флагманский смартфон Samsung',
            'price': 79990,
            'quantity': 5,
        }
    ]

    for product_data in products:
        product = Product.objects.create(**product_data)
        print(f'Created: {product.name}')

    # Тестовый пользователь
    if not User.objects.filter(username='testuser').exists():
        User.objects.create_user(
            username='testuser',
            email='test@example.com', 
            password='testpass123'
        )
        print('Created test user: testuser / testpass123')

    print("Done!")

if __name__ == '__main__':
    fill_database()