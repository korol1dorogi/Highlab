import re
from decimal import Decimal
from django.utils.text import slugify
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
import requests
from urllib.parse import urlparse
from main.models import Product, Category, ProductProperty, ProductVariant, ProductImage

def download_image_from_url(image_url, product_name):
    """
    Скачивает изображение по URL и возвращает File объект
    """
    try:
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        # Создаем временный файл
        img_temp = NamedTemporaryFile(delete=True)
        img_temp.write(response.content)
        img_temp.flush()
        
        # Получаем расширение файла из URL
        parsed_url = urlparse(image_url)
        filename = parsed_url.path.split('/')[-1]
        if not filename or '.' not in filename:
            filename = f"{slugify(product_name)}.jpg"
        
        return File(img_temp, name=filename)
    except Exception as e:
        print(f"Ошибка загрузки изображения {image_url}: {e}")
        return None

def import_product_from_parser(parser_data, category_slug=None):
    """
    Импорт товара из данных парсера
    """
    def clean_price(price_str):
        if isinstance(price_str, str):
            cleaned = re.sub(r'[^\d.]', '', price_str)
            return Decimal(cleaned) if cleaned else Decimal('0')
        return Decimal('0')
    
    # Определяем категорию
    category = None
    if category_slug:
        category = Category.objects.filter(slug=category_slug).first()
    
    if not category and parser_data.get('categories'):
        # Пытаемся найти категорию по имени
        category_name = parser_data['categories'][0]
        category = Category.objects.filter(name=category_name).first()
        
        if not category:
            # Создаем новую категорию, если не найдена
            category = Category.objects.create(
                name=category_name,
                slug=slugify(category_name)
            )
    
    # Если категория все еще не определена, используем дефолтную
    if not category:
        category = Category.objects.first()
        if not category:
            raise ValueError("Не найдена категория для товара")
    
    # Создаем или обновляем товар
    product, created = Product.objects.update_or_create(
        external_id=parser_data['id'],
        defaults={
            'category': category,
            'name': parser_data['name'],
            'slug': f"{slugify(parser_data['name'])}-{parser_data['id']}",
            'sku': parser_data['id'],
            'description': parser_data.get('description', ''),
            'base_price': clean_price(parser_data['price']),
            'available': parser_data.get('available') == 'В наличии',
            'external_url': parser_data.get('url', ''),
        }
    )
    
    # Загружаем главное изображение
    if parser_data.get('main_image') and not product.main_image:
        main_image_file = download_image_from_url(
            parser_data['main_image'], 
            parser_data['name']
        )
        if main_image_file:
            product.main_image.save(main_image_file.name, main_image_file, save=True)
    
    # Добавляем дополнительные изображения
    if parser_data.get('images'):
        # Удаляем старые изображения
        product.images.all().delete()
        
        for i, image_url in enumerate(parser_data['images']):
            if i >= 10:  # Ограничиваем количество изображений
                break
                
            image_file = download_image_from_url(image_url, parser_data['name'])
            if image_file:
                ProductImage.objects.create(
                    product=product,
                    image=image_file,
                    alt_text=parser_data['name'],
                    order=i
                )
    
    # Добавляем характеристики
    if 'properties' in parser_data:
        ProductProperty.objects.filter(product=product).delete()
        for i, (prop_name, prop_value) in enumerate(parser_data['properties'].items()):
            ProductProperty.objects.create(
                product=product,
                name=prop_name,
                value=str(prop_value),
                order=i
            )
    
    # Добавляем варианты
    if 'variants' in parser_data:
        for variant_data in parser_data['variants']:
            ProductVariant.objects.update_or_create(
                product=product,
                external_id=variant_data['variant_id'],
                defaults={
                    'name': variant_data['name'],
                    'price': clean_price(variant_data['price']),
                    'quantity': 10 if parser_data.get('available') == 'В наличии' else 0,
                    'sku': variant_data['variant_id'],
                }
            )
    
    # Обновляем общее количество
    product.total_quantity = sum(variant.quantity for variant in product.variants.all())
    product.save()
    
    action = "создан" if created else "обновлен"
    print(f"Товар '{product.name}' {action} (ID: {product.id})")
    
    return product

def import_multiple_products(products_data, category_slug=None):
    """
    Импорт нескольких товаров
    """
    results = {
        'created': 0,
        'updated': 0,
        'errors': []
    }
    
    for product_data in products_data:
        try:
            product = import_product_from_parser(product_data, category_slug)
            if product:
                if Product.objects.filter(id=product.id, created=product.created).exists():
                    results['created'] += 1
                else:
                    results['updated'] += 1
        except Exception as e:
            product_name = product_data.get('name', 'Unknown')
            error_msg = f"Ошибка импорта '{product_name}': {str(e)}"
            results['errors'].append(error_msg)
            print(error_msg)
    
    return results