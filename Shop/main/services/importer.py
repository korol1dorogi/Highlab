import requests
import os
from io import BytesIO
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from urllib.parse import urlparse
import re
from decimal import Decimal

def download_image_from_url(image_url, product_name):
    """
    Скачивает изображение по URL и возвращает File объект
    """
    try:
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        from django.utils.text import slugify
        
        # Всегда создаем имя файла на основе названия товара
        # Но пытаемся определить расширение из Content-Type
        content_type = response.headers.get('content-type', '')
        if 'jpeg' in content_type or 'jpg' in content_type:
            ext = '.jpg'
        elif 'png' in content_type:
            ext = '.png'
        elif 'gif' in content_type:
            ext = '.gif'
        elif 'webp' in content_type:
            ext = '.webp'
        else:
            # По умолчанию используем jpg
            ext = '.jpg'
        
        filename = f"{slugify(product_name)}{ext}"
        
        # Создаем файл из содержимого ответа
        image_file = File(BytesIO(response.content), name=filename)
        
        return image_file
        
    except Exception as e:
        print(f"Ошибка загрузки изображения {image_url}: {e}")
        return None

def clean_price(price_str):
    """Очистка цены от лишних символов"""
    if not price_str:
        return Decimal('0')
    
    if isinstance(price_str, str):
        # Удаляем все нецифровые символы кроме точки и запятой
        cleaned = re.sub(r'[^\d,.]', '', price_str)
        # Заменяем запятую на точку для Decimal
        cleaned = cleaned.replace(',', '.')
        try:
            return Decimal(cleaned) if cleaned else Decimal('0')
        except:
            return Decimal('0')
    return Decimal('0')