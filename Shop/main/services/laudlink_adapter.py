# shop/services/laudlink_adapter.py
import json
import re
from decimal import Decimal
from django.utils.text import slugify
from django.db.models import Q
from main.models import Category, Product, ProductProperty, ProductVariant, ProductImage
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
                        slug = LaudLinkAdapter.generate_unique_slug(temp_slug)
                        
                        # Ищем подкатегорию с учетом родительской категории
                        subcategory, created = Category.objects.get_or_create(
                            name=subcategory_data['name'],
                            parent=main_category,  # Критически важно - указываем родителя
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

    @staticmethod
    def find_correct_category(categories_list):
        """
        Находит правильную категорию для товара на основе иерархии
        С учетом того, что парсер может передавать категории в разном порядке
        
        Args:
            categories_list: список категорий товара (например: ['Dell', 'Системные блоки'])
        
        Returns:
            Category object или None
        """
        if not categories_list:
            return None
            
        print(f"Поиск категории для товара по пути: {categories_list}")
        
        # Если в списке только одна категория - ищем основную категорию
        if len(categories_list) == 1:
            category_name = categories_list[0]
            try:
                category = Category.objects.get(name=category_name, parent__isnull=True)
                print(f"Найдена основная категория: {category.name}")
                return category
            except Category.DoesNotExist:
                print(f"Основная категория '{category_name}' не найдена")
                return None
            except Category.MultipleObjectsReturned:
                print(f"Найдено несколько основных категорий с именем '{category_name}', берем первую")
                return Category.objects.filter(name=category_name, parent__isnull=True).first()
        
        # Если в списке несколько категорий - пробуем разные варианты порядка
        # Парсер может передавать: ['Dell', 'Системные блоки'] или ['Системные блоки', 'Dell']
        # Нам нужно определить правильную иерархию
        
        # Сначала попробуем стандартный порядок: первая категория - родитель, вторая - ребенок
        parent_name1 = categories_list[0]
        child_name1 = categories_list[1]
        
        try:
            # Ищем родительскую категорию
            parent_category1 = Category.objects.get(name=parent_name1, parent__isnull=True)
            print(f"Найдена родительская категория (вариант 1): {parent_category1.name}")
            
            # Ищем подкатегорию С УЧЕТОМ РОДИТЕЛЯ
            try:
                child_category1 = Category.objects.get(name=child_name1, parent=parent_category1)
                print(f"Найдена подкатегория (вариант 1): {child_category1.name} -> {parent_category1.name}")
                return child_category1
            except Category.DoesNotExist:
                print(f"Подкатегория '{child_name1}' не найдена в родительской категории '{parent_name1}'")
        except Category.DoesNotExist:
            print(f"Родительская категория '{parent_name1}' не найдена (вариант 1)")
        
        # Пробуем обратный порядок: вторая категория - родитель, первая - ребенок
        parent_name2 = categories_list[1]
        child_name2 = categories_list[0]
        
        try:
            # Ищем родительскую категорию
            parent_category2 = Category.objects.get(name=parent_name2, parent__isnull=True)
            print(f"Найдена родительская категория (вариант 2): {parent_category2.name}")
            
            # Ищем подкатегорию С УЧЕТОМ РОДИТЕЛЯ
            try:
                child_category2 = Category.objects.get(name=child_name2, parent=parent_category2)
                print(f"Найдена подкатегория (вариант 2): {child_category2.name} -> {parent_category2.name}")
                return child_category2
            except Category.DoesNotExist:
                print(f"Подкатегория '{child_name2}' не найдена в родительской категории '{parent_name2}'")
                # Возвращаем родительскую категорию как fallback
                return parent_category2
        except Category.DoesNotExist:
            print(f"Родительская категория '{parent_name2}' не найдена (вариант 2)")
        
        # Если оба варианта не сработали, ищем любую категорию по именам
        for category_name in categories_list:
            try:
                # Сначала ищем как основную категорию
                category = Category.objects.get(name=category_name, parent__isnull=True)
                print(f"Найдена основная категория (fallback): {category.name}")
                return category
            except Category.DoesNotExist:
                # Потом ищем как подкатегорию
                categories = Category.objects.filter(name=category_name)
                if categories.exists():
                    category = categories.first()
                    print(f"Найдена категория (fallback): {category.name}")
                    return category
        
        print("❌ Категория не найдена ни по одному из вариантов")
        return None

    @staticmethod
    def convert_product_data(parser_product_data):
        """
        Конвертирует данные товара из формата парсера в формат для импорта
        """
        # Определяем категорию с учетом иерархии
        categories = parser_product_data.get('categories', [])
        category = LaudLinkAdapter.find_correct_category(categories)
        
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
        Импорт одного товара из данных парсера с правильным определением категории
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
            
            # Добавляем дополнительные изображения только если их ещё нет
            # (идемпотентно — повторный импорт не перекачивает уже загруженные)
            image_urls = product_data.get('images', [])
            if image_urls and not product.images.exists():
                for i, image_url in enumerate(image_urls[:10]):  # Ограничиваем 10 изображениями
                    image_file = download_image_from_url(image_url, f"{product_data['name']}_{i}")
                    if image_file:
                        ProductImage.objects.create(
                            product=product,
                            image=image_file,
                            alt_text=product_data['name'],
                            order=i
                        )
            
            # Добавляем характеристики
            if product_data.get('properties'):
                # Удаляем старые характеристики
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
                # Удаляем старые варианты
                ProductVariant.objects.filter(product=product).delete()
                
                for variant_data in product_data['variants']:
                    # Фильтруем только настоящие варианты
                    if LaudLinkAdapter._is_real_variant(variant_data):
                        variant_id = variant_data.get('variant_id', variant_data.get('name'))
                        ProductVariant.objects.create(
                            product=product,
                            external_id=variant_id,
                            name=variant_data['name'],
                            price=clean_price(variant_data['price']),
                            quantity=10 if product_data['available'] else 0,
                            sku=variant_id,
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
        Импорт товаров из JSON файла парсера с правильным распределением по категориям
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
                    print(f"Категории товара: {product_data.get('categories', [])}")
                    
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
            
            # Статистика по категориям
            print("\n=== СТАТИСТИКА ИМПОРТА ===")
            for category in Category.objects.all():
                product_count = Product.objects.filter(category=category).count()
                parent_info = f" -> {category.parent.name}" if category.parent else " (основная)"
                print(f"Категория '{category.name}'{parent_info}: {product_count} товаров")
            
            return results
            
        except Exception as e:
            print(f"Ошибка чтения файла {json_file_path}: {e}")
            import traceback
            traceback.print_exc()
            return {'created': 0, 'updated': 0, 'errors': [str(e)]}