import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin, urlparse
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LaudLinkParser:
    def __init__(self):
        self.base_url = "https://laudlink.ru"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Для отслеживания товаров и их категорий
        self.products = {}
        self.product_categories = defaultdict(list)

    def get_full_url(self, path):
        """Преобразует относительный URL в абсолютный"""
        if path.startswith('http'):
            return path
        return urljoin(self.base_url, path)

    def parse_categories(self):
        """Парсит основные категории"""
        logger.info("Парсим основные категории...")
        try:
            response = self.session.get(self.base_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            categories_list = soup.find('div', class_='splide__list')
            
            if not categories_list:
                logger.warning("Блок с категориями не найден")
                return []
            
            slides = categories_list.find_all('div', class_='splide__slide')
            categories = []
            
            for slide in slides:
                try:
                    title_block = slide.find('div', class_='collection-preview__title')
                    if title_block:
                        a_tag = title_block.find('a')
                        if a_tag:
                            name = a_tag.text.strip()
                            url_path = a_tag.get('href', '')
                            img_tag = slide.find('img')
                            image_url = None
                            
                            if img_tag:
                                image_url = (img_tag.get('src') or 
                                           img_tag.get('data-src') or 
                                           img_tag.get('data-lazy'))
                                if image_url:
                                    # Преобразуем в абсолютный URL
                                    if image_url.startswith('//'):
                                        image_url = 'https:' + image_url
                                    elif image_url.startswith('/'):
                                        image_url = self.base_url + image_url
                                    elif not image_url.startswith('http'):
                                        image_url = self.base_url + '/' + image_url.lstrip('/')
                            
                            full_url = self.get_full_url(url_path)
                            
                            categories.append({
                                'name': name,
                                'url': full_url,
                                'image_url': image_url
                            })
                except Exception as e:
                    logger.error(f"Ошибка при обработке категории: {e}")
                    continue
            
            return categories
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге категорий: {e}")
            return []

    def parse_subcategories(self, category_url):
        """Парсит подкатегории для каждой категории"""
        logger.info(f"Парсим подкатегории: {category_url}")
        try:
            response = self.session.get(category_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            subcategories = []
            
            subcollection_list = soup.find('div', class_='subcollection-list')
            
            if subcollection_list:
                subcategory_items = subcollection_list.find_all('a', class_='subcollection-list__item')
                
                for item in subcategory_items:
                    try:
                        title_div = item.find('div', class_='subcollection-list__item-title')
                        name = title_div.text.strip() if title_div else None
                        
                        url_path = item.get('href', '')
                        img_tag = item.find('img')
                        image_url = None
                        
                        if img_tag:
                            image_url = (img_tag.get('src') or 
                                       img_tag.get('data-src') or 
                                       img_tag.get('data-lazy'))
                            if image_url:
                                # Преобразуем в абсолютный URL
                                if image_url.startswith('//'):
                                    image_url = 'https:' + image_url
                                elif image_url.startswith('/'):
                                    image_url = self.base_url + image_url
                                elif not image_url.startswith('http'):
                                    image_url = self.base_url + '/' + image_url.lstrip('/')
                        
                        full_url = self.get_full_url(url_path)
                        
                        if name and full_url:
                            subcategories.append({
                                'name': name,
                                'url': full_url,
                                'image_url': image_url
                            })
                    except Exception as e:
                        logger.error(f"Ошибка при обработке подкатегории: {e}")
                        continue
            
            return subcategories
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге подкатегорий: {e}")
            return []

    def parse_products_from_page(self, page_url, main_category, subcategory=None):
        """Парсит товары со страницы категории или подкатегории"""
        logger.info(f"Парсим товары со страницы: {page_url}")
        try:
            response = self.session.get(page_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            products_data = []
            
            # Находим все товары на странице
            product_forms = soup.find_all('form', class_='product-preview')
            
            for form in product_forms:
                try:
                    # Извлекаем основные данные из превью
                    product_data = self.parse_product_preview(form, main_category, subcategory)
                    if product_data:
                        products_data.append(product_data)
                        
                except Exception as e:
                    logger.error(f"Ошибка при обработке товара: {e}")
                    continue
            
            return products_data
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге страницы товаров: {e}")
            return []

    def parse_product_preview(self, form, main_category, subcategory=None):
        """Парсит данные товара из превью на странице категории"""
        try:
            # ID товара
            product_id = form.get('data-product-id')
            
            # Название и ссылка
            title_block = form.find('div', class_='product-preview__title')
            if not title_block:
                return None
                
            a_tag = title_block.find('a')
            name = a_tag.text.strip() if a_tag else None
            product_url = a_tag.get('href') if a_tag else None
            
            if not name or not product_url:
                return None
                
            full_product_url = self.get_full_url(product_url)
            
            # Цена
            price_block = form.find('div', class_='product-preview__price')
            price = None
            if price_block:
                price_cur = price_block.find('span', class_='product-preview__price-cur')
                if price_cur:
                    price = price_cur.text.strip()
            
            # Изображение
            image_url = None
            img_tag = form.find('img')
            if img_tag:
                image_url = (img_tag.get('src') or 
                           img_tag.get('data-src') or 
                           img_tag.get('data-lazy'))
                if image_url:
                    # Преобразуем в абсолютный URL
                    if image_url.startswith('//'):
                        image_url = 'https:' + image_url
                    elif image_url.startswith('/'):
                        image_url = self.base_url + image_url
                    elif not image_url.startswith('http'):
                        image_url = self.base_url + '/' + image_url.lstrip('/')
            
            # Наличие
            available_block = form.find('div', class_='product-preview__available')
            available = available_block.text.strip() if available_block else None
            
            # Формируем категории как плоский массив
            categories = [main_category]
            if subcategory:
                categories.append(subcategory)
            
            product_data = {
                'id': product_id,
                'name': name,
                'url': full_product_url,
                'price': price,
                'image_url': image_url,
                'available': available,
                'categories': categories
            }
            
            return product_data
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге превью товара: {e}")
            return None

    def parse_product_with_variants(self, product_url):
        """Комплексный парсинг товара с вариантами"""
        logger.info(f"Комплексный парсинг товара: {product_url}")
        try:
            response = self.session.get(product_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            details = {
                'name': self._parse_name(soup),
                'price': None,
                'images': self._parse_all_images(soup),
                'properties': self._parse_properties(soup),
                'description': self._parse_description(soup),
                'variants': [],
                'url': product_url
            }
            
            details['main_image'] = details['images'][0] if details['images'] else None
            
            # Комплексный парсинг вариантов и цен
            variants_data = self._comprehensive_variant_parsing(soup, product_url)
            details['variants'] = variants_data
            
            # Устанавливаем основную цену
            if variants_data:
                details['price'] = variants_data[0].get('price')
            else:
                details['price'] = self._parse_price(soup)
            
            return details
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге товара {product_url}: {e}")
            return {}

    def _comprehensive_variant_parsing(self, soup, product_url):
        """Комплексный парсинг вариантов всеми доступными методами"""
        variants = []
        
        # Метод 1: Парсинг из select элемента (самый надежный)
        select_variants = self._parse_variants_from_select(soup)
        variants.extend(select_variants)
        
        # Метод 2: Парсинг из option-selector
        option_selector_variants = self._parse_variants_from_option_selector(soup)
        variants.extend(option_selector_variants)
        
        # Метод 3: Поиск данных в data-атрибутах (только для дополнения)
        data_attr_variants = self._parse_variants_from_data_attributes(soup)
        variants.extend(data_attr_variants)
        
        # Метод 4: Поиск в микроразметке (только для дополнения)
        microdata_variants = self._parse_variants_from_microdata(soup)
        variants.extend(microdata_variants)
        
        # Обработка и объединение дубликатов
        variants = self._merge_variants(variants)
        
        # ФИЛЬТРАЦИЯ: оставляем только настоящие варианты
        variants = self._filter_real_variants(variants)
        
        # Если вариантов нет, создаем базовый вариант
        if not variants:
            variants = [self._create_base_variant(soup, product_url)]
        
        return variants

    def _filter_real_variants(self, variants):
        """Фильтрует только настоящие варианты товара"""
        real_variants = []
        
        for variant in variants:
            if self._is_real_variant(variant):
                real_variants.append(variant)
        
        return real_variants

    def _is_real_variant(self, variant):
        """Определяет, является ли вариант настоящим вариантом товара"""
        name = variant.get('name', '')
        variant_id = variant.get('variant_id')
        price = variant.get('price')
        source = variant.get('source')
        
        # КРИТЕРИИ ДЛЯ ФИЛЬТРАЦИИ НАСТОЯЩИХ ВАРИАНТОВ:
        
        # 1. Должен иметь variant_id (кроме случаев, когда источник надежный)
        if not variant_id and source not in ['option_selector', 'microdata']:
            return False
        
        # 2. Название не должно быть слишком длинным (мусорные варианты часто имеют длинные названия)
        if len(name) > 100:
            return False
        
        # 3. Название должно содержать характерные для вариантов паттерны
        variant_patterns = [
            r'\d+\s*[ГгTТ][Бб]',  # цифры + ГБ/ТБ
            r'\d+\s*[GgTt][Bb]',  # цифры + GB/TB
            r'\d+\s*[Мм]?[Бб]',   # цифры + МБ
            r'/\s*\d',             # слеш с цифрами после
            r'\d+\s*[xх×]\s*\d',   # размеры типа 16x9
            r'\d+\s*GB',           # явно GB
            r'\d+\s*TB',           # явно TB
        ]
        
        has_variant_pattern = any(re.search(pattern, name, re.IGNORECASE) for pattern in variant_patterns)
        
        # 4. Исключаем явно мусорные названия
        garbage_patterns = [
            r'выбрать',
            r'выбор',
            r'tdp',
            r'память:',
            r'разъемы:',
            r'автономность',
            r'офисные задачи',
            r'нагрузка',
            r'выберите',
            r'select',
            r'choose',
        ]
        
        has_garbage = any(re.search(pattern, name, re.IGNORECASE) for pattern in garbage_patterns)
        
        # 5. Цена должна быть адекватной (если есть)
        if price:
            # Ищем числовое значение цены
            price_match = re.search(r'(\d[\d\s]*)', str(price))
            if price_match:
                price_value = float(price_match.group(1).replace(' ', ''))
                # Цена должна быть разумной для товара (не 9 рублей и не миллионы)
                if price_value < 100 or price_value > 10000000:
                    return False
        
        # ЛОГИКА ПРИНЯТИЯ РЕШЕНИЯ:
        # - Если есть variant_id И цена И нет мусора в названии - принимаем
        if variant_id and price and not has_garbage:
            return True
        
        # - Если источник 'select' или 'jsonld' - принимаем (это надежные источники)
        if source in ['select', 'jsonld']:
            return True
        
        # - Если есть паттерн варианта И нет мусора И есть цена - принимаем
        if has_variant_pattern and not has_garbage and price:
            return True
        
        # - Если источник 'option_selector' и есть паттерн варианта - принимаем
        if source == 'option_selector' and has_variant_pattern:
            return True
        
        return False

    def _parse_variants_from_select(self, soup):
        """Парсинг вариантов из select элемента"""
        variants = []
        select = soup.find('select', {'name': 'variant_id'})
        
        if select:
            options = select.find_all('option')
            for option in options:
                variant_id = option.get('value')
                variant_name = option.text.strip()
                
                if variant_id and variant_id != '' and variant_name:
                    # Пытаемся извлечь цену из data-атрибутов
                    price = option.get('data-price')
                    
                    variants.append({
                        'variant_id': variant_id,
                        'name': variant_name,
                        'price': price,
                        'source': 'select'
                    })
        
        return variants

    def _parse_variants_from_option_selector(self, soup):
        """Парсинг вариантов из интерактивного option-selector"""
        variants = []
        
        option_selector = soup.find('div', {'data-option-selector': ''})
        if not option_selector:
            return variants
        
        # Собираем информацию об опциях
        options_info = []
        option_blocks = option_selector.find_all('div', class_='option')
        
        for option_block in option_blocks:
            option_name = option_block.find('label', class_='option-label')
            if not option_name:
                continue
                
            option_name = option_name.text.strip()
            values = []
            
            value_buttons = option_block.find_all('button', class_='option-value')
            for btn in value_buttons:
                value_text = btn.text.strip()
                value_data = {
                    'text': value_text,
                    'is_active': 'is-active' in btn.get('class', []),
                    'data': {
                        'option_bind': btn.get('data-option-bind'),
                        'option_id': btn.get('data-option-id'),
                        'value_id': btn.get('data-value-id'),
                        'value': btn.get('value')
                    }
                }
                values.append(value_data)
            
            options_info.append({
                'name': option_name,
                'values': values
            })
        
        # Генерируем варианты на основе активных значений
        active_variant = self._generate_variant_from_active_options(options_info)
        if active_variant:
            variants.append(active_variant)
        
        return variants

    def _generate_variant_from_active_options(self, options_info):
        """Генерирует вариант из активных опций"""
        active_parts = []
        options_dict = {}
        
        for option in options_info:
            active_value = next((v for v in option['values'] if v['is_active']), None)
            if active_value:
                active_parts.append(f"{option['name']}: {active_value['text']}")
                options_dict[option['name']] = active_value['text']
        
        if active_parts:
            return {
                'name': ' / '.join(active_parts),
                'options': options_dict,
                'price': None,
                'source': 'option_selector'
            }
        
        return None

    def _parse_variants_from_data_attributes(self, soup):
        """Поиск данных о вариантах в data-атрибутах"""
        variants = []
        
        # Ищем элементы с data-атрибутами, связанными с вариантами
        data_patterns = [
            '[data-variant]',
            '[data-product-variants]',
            '[data-variants]',
            '[data-options]',
            '[data-variant-id]',
            '[data-variant-price]'
        ]
        
        for pattern in data_patterns:
            elements = soup.select(pattern)
            for elem in elements:
                variant_data = self._extract_variant_from_data_attrs(elem)
                if variant_data:
                    variants.append(variant_data)
        
        return variants

    def _extract_variant_from_data_attrs(self, element):
        """Извлекает данные варианта из data-атрибутов элемента"""
        data = {}
        
        # Собираем все data-атрибуты
        for attr_name, attr_value in element.attrs.items():
            if attr_name.startswith('data-'):
                data[attr_name] = attr_value
        
        # Пытаемся собрать вариант из данных
        variant_id = data.get('data-variant-id') or data.get('data-variant')
        price = data.get('data-variant-price') or data.get('data-price')
        name = element.get_text(strip=True)
        
        if variant_id or name:
            return {
                'variant_id': variant_id,
                'name': name if name else f"Вариант {variant_id}",
                'price': price,
                'source': 'data_attributes'
            }
        
        return None

    def _parse_variants_from_microdata(self, soup):
        """Парсинг вариантов из микроразметки"""
        variants = []
        
        # Ищем микроразметку Schema.org
        product_offers = soup.find_all(['div', 'span'], {'itemtype': 'http://schema.org/Offer'})
        
        for offer in product_offers:
            variant_data = self._extract_variant_from_microdata(offer)
            if variant_data:
                variants.append(variant_data)
        
        # Ищем JSON-LD
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                data = json.loads(script.string)
                microdata_variants = self._extract_variants_from_jsonld(data)
                variants.extend(microdata_variants)
            except:
                continue
        
        return variants

    def _extract_variant_from_microdata(self, offer_element):
        """Извлекает вариант из микроразметки"""
        price_element = offer_element.find(attrs={'itemprop': 'price'})
        price_currency = offer_element.find(attrs={'itemprop': 'priceCurrency'})
        name_element = offer_element.find(attrs={'itemprop': 'name'})
        sku_element = offer_element.find(attrs={'itemprop': 'sku'})
        
        price = None
        if price_element:
            price = price_element.get('content') or price_element.text.strip()
            if price_currency:
                currency = price_currency.get('content') or price_currency.text.strip()
                price = f"{price} {currency}"
        
        name = None
        if name_element:
            name = name_element.get('content') or name_element.text.strip()
        
        variant_id = None
        if sku_element:
            variant_id = sku_element.get('content') or sku_element.text.strip()
        
        if price or name or variant_id:
            return {
                'variant_id': variant_id,
                'name': name or f"Вариант {variant_id}" if variant_id else "Основной вариант",
                'price': price,
                'source': 'microdata'
            }
        
        return None

    def _extract_variants_from_jsonld(self, data):
        """Извлекает варианты из JSON-LD"""
        variants = []
        
        if isinstance(data, dict):
            # Обрабатываем одиночный продукт
            if data.get('@type') == 'Product':
                offers = data.get('offers')
                if isinstance(offers, dict):
                    variant = self._create_variant_from_offer(offers, data.get('name'))
                    if variant:
                        variants.append(variant)
                elif isinstance(offers, list):
                    for offer in offers:
                        variant = self._create_variant_from_offer(offer, data.get('name'))
                        if variant:
                            variants.append(variant)
            
            # Обрабатываем список продуктов
            elif isinstance(data.get('@graph'), list):
                for item in data['@graph']:
                    if item.get('@type') == 'Product':
                        offers_variants = self._extract_variants_from_jsonld(item)
                        variants.extend(offers_variants)
        
        return variants

    def _create_variant_from_offer(self, offer, product_name):
        """Создает вариант из предложения"""
        price = offer.get('price')
        price_currency = offer.get('priceCurrency', '₽')
        sku = offer.get('sku')
        name = offer.get('name')
        
        if price:
            full_price = f"{price} {price_currency}"
            variant_name = name or f"{product_name} - {sku}" if product_name and sku else "Основной вариант"
            
            return {
                'variant_id': sku,
                'name': variant_name,
                'price': full_price,
                'source': 'jsonld'
            }
        
        return None

    def _merge_variants(self, variants):
        """Объединяет дублирующиеся варианты"""
        merged = {}
        
        for variant in variants:
            key = variant.get('variant_id') or variant.get('name')
            if not key:
                continue
                
            if key not in merged:
                merged[key] = variant
            else:
                # Объединяем данные, отдавая предпочтение не-None значениям
                existing = merged[key]
                for field in ['price', 'variant_id']:
                    if not existing.get(field) and variant.get(field):
                        existing[field] = variant[field]
                # Объединяем источники
                existing_sources = existing.get('sources', [existing.get('source', 'unknown')])
                new_source = variant.get('source', 'unknown')
                if new_source not in existing_sources:
                    existing_sources.append(new_source)
                existing['sources'] = existing_sources
        
        return list(merged.values())

    def _create_base_variant(self, soup, product_url):
        """Создает базовый вариант, если другие методы не сработали"""
        price = self._parse_price(soup)
        name = self._parse_name(soup) or "Основной вариант"
        
        return {
            'name': name,
            'price': price,
            'source': 'base',
            'variant_id': 'base'
        }

    def _parse_name(self, soup):
        """Парсит название товара"""
        title_block = soup.find('h1', class_='product__title')
        return title_block.text.strip() if title_block else None

    def _parse_price(self, soup):
        """Парсит цену товара"""
        # Основной блок цены
        price_block = soup.find('div', class_='product__price')
        if price_block:
            price_cur = price_block.find('span', class_='product__price-cur')
            if price_cur and price_cur.text.strip():
                return price_cur.text.strip()
        
        # Data-атрибуты
        price_elements = soup.find_all(attrs={"data-product-card-price-from-cart": True})
        for elem in price_elements:
            if elem.text.strip():
                return elem.text.strip()
        
        # Любой элемент с классом содержащим "price"
        price_elements = soup.find_all(class_=re.compile(r'price'))
        for elem in price_elements:
            text = elem.get_text(strip=True)
            if text and any(c.isdigit() for c in text):
                return text
        
        return None

    def _parse_all_images(self, soup):
        """Парсит все изображения товара"""
        images = []
        
        # Основной слайдер
        gallery_main = soup.find('div', class_='product__gallery-main')
        if gallery_main:
            img_tags = gallery_main.find_all('img')
            for img in img_tags:
                src = self._get_image_src(img)
                if src and src not in images:
                    images.append(src)
        
        # Миниатюры
        gallery_thumbs = soup.find('div', class_='product__gallery-tumbs')
        if gallery_thumbs:
            img_tags = gallery_thumbs.find_all('img')
            for img in img_tags:
                src = self._get_image_src(img)
                if src and src not in images:
                    images.append(src)
        
        # Скрытый блок
        gallery_all = soup.find('div', class_='js-product-all-images')
        if gallery_all:
            img_tags = gallery_all.find_all('img')
            for img in img_tags:
                src = self._get_image_src(img)
                if src and src not in images:
                    images.append(src)
        
        return images

    def _get_image_src(self, img_tag):
        src = (img_tag.get('src') or 
              img_tag.get('data-src') or 
              img_tag.get('data-lazy') or
              img_tag.get('data-original'))
        
        if src and src.startswith('//'):
            src = 'https:' + src
        elif src and src.startswith('/'):
            src = self.base_url + src
        elif src and not src.startswith('http'):
            src = self.base_url + '/' + src.lstrip('/')
            
        return src

    def _parse_properties(self, soup):
        properties = {}
        properties_block = soup.find('div', class_='product__properties-items')
        if properties_block:
            property_items = properties_block.find_all('div', class_='product__property')
            for item in property_items:
                name_div = item.find('div', class_='product__property-name')
                value_div = item.find('div', class_='product__property-value')
                if name_div and value_div:
                    prop_name = name_div.text.strip().rstrip(':')
                    prop_value = value_div.text.strip()
                    properties[prop_name] = prop_value
        return properties

    def _parse_description(self, soup):
        description_text = None
        description_block = soup.find('div', class_='product__short-description')
        if description_block:
            description_text = description_block.get_text(strip=True)
        
        if not description_text:
            description_selectors = [
                '.product__description-content',
                '.static-text',
                '[class*="description"]'
            ]
            for selector in description_selectors:
                desc_block = soup.select_one(selector)
                if desc_block:
                    description_text = desc_block.get_text(strip=True)
                    if description_text:
                        break
        
        return description_text

    def handle_pagination(self, category_url, main_category, subcategory=None):
        """Обрабатывает пагинацию в категории или подкатегории"""
        all_products = []
        page = 1
        
        while True:
            if page == 1:
                current_url = category_url
            else:
                # Добавляем параметр page к URL
                parsed_url = urlparse(category_url)
                if '?' in category_url:
                    current_url = f"{category_url}&page={page}"
                else:
                    current_url = f"{category_url}?page={page}"
            
            logger.info(f"Обрабатываем страницу {page}: {current_url}")
            
            products = self.parse_products_from_page(current_url, main_category, subcategory)
            
            if not products:
                break
                
            all_products.extend(products)
            
            # Проверяем есть ли следующая страница
            response = self.session.get(current_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Ищем признаки следующей страницы
            next_page = soup.find('a', class_='pagination__next')
            if not next_page:
                break
                
            page += 1
            time.sleep(1)  # Задержка между страницами
        
        return all_products

    def parse_all_products(self, categories_with_subcategories, limit=None):
        """Парсит все товары из всех категорий и подкатегорий с поддержкой вариантов.
        limit — необязательное ограничение числа товаров (для тестовых прогонов)."""
        all_products_dict = {}  # Используем dict для объединения товаров по ID
        
        for category in categories_with_subcategories:
            category_name = category['name']
            category_url = category['url']
            subcategories = category.get('subcategories', [])
            
            # Парсим товары из основной категории
            logger.info(f"\nОбрабатываем основную категорию: {category_name}")
            main_category_products = self.handle_pagination(category_url, category_name)
            
            # Обновляем информацию о товарах из основной категории
            for product in main_category_products:
                product_id = product['id']
                
                if product_id in all_products_dict:
                    # Товар уже есть, объединяем категории
                    existing_product = all_products_dict[product_id]
                    
                    # Объединяем категории, убирая дубликаты
                    existing_categories = set(existing_product['categories'])
                    new_categories = set(product['categories'])
                    merged_categories = list(existing_categories.union(new_categories))
                    
                    existing_product['categories'] = merged_categories
                else:
                    # Новый товар, парсим детали с вариантами
                    time.sleep(1)  # Задержка между запросами к товарам
                    details = self.parse_product_with_variants(product['url'])
                    
                    # Объединяем данные
                    full_product_data = {**product, **details}
                    all_products_dict[product_id] = full_product_data

                    if limit and len(all_products_dict) >= limit:
                        logger.info(f"Достигнут лимит товаров ({limit}) — останавливаемся.")
                        return list(all_products_dict.values())

            # Парсим товары из подкатегорий
            for subcategory in subcategories:
                subcategory_name = subcategory['name']
                subcategory_url = subcategory['url']
                
                logger.info(f"Обрабатываем подкатегорию: {category_name} -> {subcategory_name}")
                
                # Парсим товары из подкатегории (с пагинацией)
                subcategory_products = self.handle_pagination(subcategory_url, category_name, subcategory_name)
                
                # Обновляем информацию о товарах
                for product in subcategory_products:
                    product_id = product['id']
                    
                    if product_id in all_products_dict:
                        # Товар уже есть, объединяем категории
                        existing_product = all_products_dict[product_id]
                        
                        # Объединяем категории, убирая дубликаты
                        existing_categories = set(existing_product['categories'])
                        new_categories = set(product['categories'])
                        merged_categories = list(existing_categories.union(new_categories))
                        
                        existing_product['categories'] = merged_categories
                    else:
                        # Новый товар, парсим детали с вариантами
                        time.sleep(1)  # Задержка между запросами к товарам
                        details = self.parse_product_with_variants(product['url'])
                        
                        # Объединяем данные
                        full_product_data = {**product, **details}
                        all_products_dict[product_id] = full_product_data

                        if limit and len(all_products_dict) >= limit:
                            logger.info(f"Достигнут лимит товаров ({limit}) — останавливаемся.")
                            return list(all_products_dict.values())

        return list(all_products_dict.values())

    def save_to_json(self, data, filename):
        """Сохраняет данные в JSON файл"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Данные сохранены в {filename}")

def main():
    import argparse
    import os

    ap = argparse.ArgumentParser(description='Парсер интернет-магазина laudlink.ru')
    ap.add_argument('--limit', type=int, default=None,
                    help='Ограничить число товаров (для тестового прогона)')
    ap.add_argument('--output-dir', default='.',
                    help='Папка для сохранения JSON (по умолчанию текущая)')
    args = ap.parse_args()

    out_dir = args.output_dir
    os.makedirs(out_dir, exist_ok=True)
    categories_path = os.path.join(out_dir, 'categories_structure.json')
    products_path = os.path.join(out_dir, 'all_products_with_variants.json')

    parser = LaudLinkParser()

    logger.info("Начинаем парсинг сайта laudlink.ru...")
    if args.limit:
        logger.info(f"Режим теста: лимит {args.limit} товаров")

    # 1. Парсим основные категории
    categories = parser.parse_categories()
    logger.info(f"Найдено основных категорий: {len(categories)}")

    # 2. Парсим подкатегории для каждой категории
    categories_with_subcategories = []
    for category in categories:
        logger.info(f"Обрабатываем категорию: {category['name']}")
        subcategories = parser.parse_subcategories(category['url'])
        category['subcategories'] = subcategories
        categories_with_subcategories.append(category)
        time.sleep(1)  # Задержка между категориями

    # Сохраняем структуру категорий
    parser.save_to_json(categories_with_subcategories, categories_path)

    # 3. Парсим все товары с поддержкой вариантов (из всех категорий и подкатегорий)
    logger.info("\nНачинаем парсинг товаров с вариантами...")
    all_products = parser.parse_all_products(categories_with_subcategories, limit=args.limit)

    # 4. Сохраняем товары
    parser.save_to_json(all_products, products_path)
    
    # Статистика
    total_products = len(all_products)
    total_categories = len(categories_with_subcategories)
    total_subcategories = sum(len(cat['subcategories']) for cat in categories_with_subcategories)
    
    # Подсчет товаров с вариантами
    products_with_variants = sum(1 for product in all_products 
                               if product.get('variants') and len(product['variants']) > 1)
    
    logger.info(f"\nПарсинг завершен!")
    logger.info(f"Обработано:")
    logger.info(f"- Категорий: {total_categories}")
    logger.info(f"- Подкатегорий: {total_subcategories}")
    logger.info(f"- Товаров: {total_products}")
    logger.info(f"- Товаров с вариантами: {products_with_variants}")

if __name__ == "__main__":
    main()