# shop/services/laudlink_adapter.py
import json
import re
from decimal import Decimal
from django.utils.text import slugify
from main.models import Category, Product, ProductProperty, ProductVariant, ProductImage  # ИЗМЕНИЛИ main.models на shop.models
from .importer import download_image_from_url, clean_price

class LaudLinkAdapter:
    """
    Адаптер для преобразования данных из вашего парсера в формат Django моделей
    """
    
    @staticmethod
    def generate_unique_slug(name, parent=None):
        """Генерирует уникальный slug с учетом родительской категории"""
        base_slug = slugify(name) or "category"
        slug = base_slug
        counter = 1
    
        # Проверяем уникальность slug
        while Category.objects.filter(slug=slug).exists():
            # Используем более предсказуемый формат
            slug = f"{base_slug}-{counter}"
            counter += 1

            # Защита от бесконечного цикла
            if counter > 1000:
                # Если не удалось найти уникальный slug за 1000 попыток,
                # добавляем временную метку
                import time
                slug = f"{base_slug}-{int(time.time())}"
                break
    
        print(f"Сгенерирован slug: '{slug}' для категории '{name}'")
        return slug
    
    @staticmethod
    def import_categories_from_json(json_file_path, update_images=True):
        """
        Импорт категорий из JSON файла, созданного парсером
    
        :param update_images: обновлять ли изображения существующих категорий
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                categories_data = json.load(f)
        
            created_count = 0
            updated_count = 0
        
            # Сначала создаем все основные категории
            for category_data in categories_data:
                # Создаем основную категорию
                print(category_data['url'])
                temp_slug = category_data['url'].split('/')[-1]
                #slug = LaudLinkAdapter.generate_unique_slug(category_data['name'])
                slug = LaudLinkAdapter.generate_unique_slug(temp_slug)
                main_category, created = Category.objects.get_or_create(
                    name=category_data['name'],
                    defaults={
                        'slug': slug,
                        'description': f"Категория {category_data['name']}",
                    }
                )
            
                # Загружаем/обновляем изображение категории
                image_url = category_data.get('image_url')
                if image_url and (created or update_images):
                    try:
                        image_file = download_image_from_url(image_url, category_data['name'])
                        if image_file:
                            # Если изображение уже есть, удаляем старое
                            if main_category.image:
                                main_category.image.delete(save=False)
                            main_category.image.save(image_file.name, image_file, save=True)
                            print(f"Изображение категории '{category_data['name']}' загружено")
                    except Exception as e:
                        print(f"Ошибка загрузки изображения категории '{category_data['name']}': {e}")
            
                if created:
                    created_count += 1
                    print(f"Создана категория: {category_data['name']}")
                else:
                    updated_count += 1
        
            # Затем создаем подкатегории
            for category_data in categories_data:
                try:
                    
                    main_category = Category.objects.get(name=category_data['name'])
                
                    # Создаем подкатегории
                    for subcategory_data in category_data.get('subcategories', []):
                        temp_slug = subcategory_data['url'].split('/')[-1]
                        #slug = LaudLinkAdapter.generate_unique_slug(subcategory_data['name'])
                        slug = LaudLinkAdapter.generate_unique_slug(temp_slug)
                        subcategory, created = Category.objects.get_or_create(
                            name=subcategory_data['name'],
                            parent=main_category,
                            defaults={
                                'slug': slug,
                                'description': f"Подкатегория {subcategory_data['name']}",
                            }
                        )
                    
                        # Загружаем/обновляем изображение подкатегории
                        image_url = subcategory_data.get('image_url')
                        if image_url and (created or update_images):
                            try:
                                image_file = download_image_from_url(image_url, subcategory_data['name'])
                                if image_file:
                                # Если изображение уже есть, удаляем старое
                                    if subcategory.image:
                                        subcategory.image.delete(save=False)
                                    subcategory.image.save(image_file.name, image_file, save=True)
                                    print(f"Изображение подкатегории '{subcategory_data['name']}' загружено")
                            except Exception as e:
                                print(f"Ошибка загрузки изображения подкатегории '{subcategory_data['name']}': {e}")
                    
                        if created:
                            created_count += 1
                            print(f"Создана подкатегория: {subcategory_data['name']} -> {category_data['name']}")
                        else:
                            updated_count += 1
                        
                except Category.DoesNotExist:
                    print(f"Основная категория {category_data['name']} не найдена")
                    continue
        
            return {
                'created': created_count,
                'updated': updated_count,
                'total': created_count + updated_count
            }
        
        except Exception as e:
            print(f"Ошибка импорта категорий: {e}")
            import traceback
            traceback.print_exc()
            return None

    # Остальные методы остаются без изменений...
    @staticmethod
    def convert_product_data(parser_product_data):
        """
        Конвертирует данные товара из формата парсера в формат для импорта
        """
        # Определяем категорию
        categories = parser_product_data.get('categories', [])
        category = None
        
        if categories:
            # Берем последнюю категорию как самую конкретную
            category_name = categories[-1] if categories else categories[0] if categories else None
            if category_name:
                try:
                    category = Category.objects.filter(name=category_name).first()
                except Category.DoesNotExist:
                    # Если категория не найдена, создаем ее
                    slug = LaudLinkAdapter.generate_unique_slug(category_name)
                    category = Category.objects.create(
                        name=category_name,
                        slug=slug,
                        description=f"Категория {category_name}"
                    )
                    print(f"Создана новая категория: {category_name}")
        
        # Если категория не определена, используем первую доступную
        if not category:
            category = Category.objects.first()
            if not category:
                # Создаем дефолтную категорию
                category = Category.objects.create(
                    name="Разное",
                    slug="raznoe",
                    description="Разные товары"
                )
                print("Создана дефолтная категория 'Разное'")
        
        # Подготавливаем данные для импорта
        product_data = {
            'id': parser_product_data['id'],
            'name': parser_product_data['name'],
            'url': parser_product_data.get('url', ''),
            'price': parser_product_data.get('price'),
            'image_url': parser_product_data.get('image_url'),
            'available': parser_product_data.get('available') == 'В наличии',
            'categories': categories,
            'images': parser_product_data.get('images', []),
            'properties': parser_product_data.get('properties', {}),
            'description': parser_product_data.get('description', ''),
            'variants': parser_product_data.get('variants', []),
            'main_image': parser_product_data.get('main_image')
        }
        
        return product_data, category

    @staticmethod
    def import_product_from_parser_data(parser_product_data):
        """
        Импорт одного товара из данных парсера
        """
        try:
            # Конвертируем данные
            product_data, category = LaudLinkAdapter.convert_product_data(parser_product_data)
            
            # Генерируем уникальный slug
            base_slug = slugify(product_data['name'])
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            # Создаем или обновляем товар
            product, created = Product.objects.update_or_create(
                external_id=product_data['id'],
                defaults={
                    'category': category,
                    'name': product_data['name'],
                    'slug': slug,
                    'sku': product_data['id'],
                    'description': product_data['description'],
                    'base_price': clean_price(product_data['price']),
                    'available': product_data['available'],
                    'external_url': product_data['url'],
                }
            )
            
            # Загружаем главное изображение
            main_image_url = product_data.get('main_image') or product_data.get('image_url')
            if main_image_url and not product.main_image:
                main_image_file = download_image_from_url(main_image_url, product_data['name'])
                if main_image_file:
                    product.main_image.save(main_image_file.name, main_image_file, save=True)
            
            # Добавляем дополнительные изображения
            image_urls = product_data.get('images', [])
            if image_urls:
                product.images.all().delete()
                
                for i, image_url in enumerate(image_urls[:10]):
                    image_file = download_image_from_url(image_url, product_data['name'])
                    if image_file:
                        ProductImage.objects.create(
                            product=product,
                            image=image_file,
                            alt_text=product_data['name'],
                            order=i
                        )
            
            # Добавляем характеристики
            if product_data.get('properties'):
                ProductProperty.objects.filter(product=product).delete()
                for i, (prop_name, prop_value) in enumerate(product_data['properties'].items()):
                    ProductProperty.objects.create(
                        product=product,
                        name=prop_name,
                        value=str(prop_value),
                        order=i
                    )
            
            # Добавляем варианты
            if product_data.get('variants'):
                for variant_data in product_data['variants']:
                    # Фильтруем только настоящие варианты (как в вашем парсере)
                    if LaudLinkAdapter._is_real_variant(variant_data):
                        variant_id = variant_data.get('variant_id', variant_data.get('name'))
                        ProductVariant.objects.update_or_create(
                            product=product,
                            external_id=variant_id,
                            defaults={
                                'name': variant_data['name'],
                                'price': clean_price(variant_data['price']),
                                'quantity': 10 if product_data['available'] else 0,
                                'sku': variant_id,
                            }
                        )
            
            # Обновляем общее количество
            product.total_quantity = sum(variant.quantity for variant in product.variants.all())
            product.save()
            
            action = "создан" if created else "обновлен"
            print(f"Товар '{product.name}' {action} в категории '{category.name}'")
            
            return product
            
        except Exception as e:
            print(f"Ошибка импорта товара {parser_product_data.get('name', 'Unknown')}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def _is_real_variant(variant_data):
        """Фильтрация настоящих вариантов (аналогично вашему парсеру)"""
        name = variant_data.get('name', '')
        variant_id = variant_data.get('variant_id')
        
        # Паттерны для вариантов
        variant_patterns = [
            r'\d+\s*[ГгTТ][Бб]',
            r'\d+\s*[GgTt][Bb]', 
            r'\d+\s*[Мм]?[Бб]',
            r'/\s*\d',
            r'\d+\s*[xх×]\s*\d',
            r'\d+\s*GB',
            r'\d+\s*TB',
        ]
        
        # Мусорные паттерны
        garbage_patterns = [
            r'выбрать',
            r'выбор', 
            r'tdp',
            r'память:',
            r'разъемы:',
            r'автономность',
            r'офисные задачи',
            r'нагрузка',
        ]
        
        has_variant_pattern = any(re.search(pattern, name, re.IGNORECASE) for pattern in variant_patterns)
        has_garbage = any(re.search(pattern, name, re.IGNORECASE) for pattern in garbage_patterns)
        
        # Логика принятия решения
        if variant_id and not has_garbage:
            return True
        
        if has_variant_pattern and not has_garbage:
            return True
        
        return False
    
    @staticmethod
    def import_products_from_json(json_file_path, limit=None):
        """
        Импорт товаров из JSON файла парсера
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                products_data = json.load(f)
            
            if isinstance(products_data, dict):
                products_data = [products_data]
            
            results = {
                'created': 0,
                'updated': 0,
                'errors': []
            }
            
            # Ограничиваем количество, если указано limit
            if limit:
                products_data = products_data[:limit]
            
            print(f"Начинаем импорт {len(products_data)} товаров...")
            
            for i, product_data in enumerate(products_data, 1):
                try:
                    print(f"Импортируем товар {i}/{len(products_data)}: {product_data.get('name', 'Unknown')}")
                    
                    product = LaudLinkAdapter.import_product_from_parser_data(product_data)
                    
                    if product:
                        # Проверяем, был ли товар только что создан
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
            
        except Exception as e:
            print(f"Ошибка чтения файла {json_file_path}: {e}")
            import traceback
            traceback.print_exc()
            return {'created': 0, 'updated': 0, 'errors': [str(e)]}