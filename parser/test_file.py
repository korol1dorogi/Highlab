import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin, urlparse
from collections import defaultdict

class LaudLinkParser:
    def __init__(self):
        self.base_url = "https://laudlink.ru"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
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
        print("Парсим основные категории...")
        try:
            response = self.session.get(self.base_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            categories_list = soup.find('div', class_='splide__list')
            
            if not categories_list:
                print("Блок с категориями не найден")
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
                            image_url = img_tag.get('src') if img_tag else None
                            
                            full_url = self.get_full_url(url_path)
                            
                            categories.append({
                                'name': name,
                                'url': full_url,
                                'image_url': image_url
                            })
                except Exception as e:
                    print(f"Ошибка при обработке категории: {e}")
                    continue
            
            return categories
            
        except Exception as e:
            print(f"Ошибка при парсинге категорий: {e}")
            return []

    def parse_subcategories(self, category_url):
        """Парсит подкатегории для каждой категории"""
        print(f"Парсим подкатегории: {category_url}")
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
                        image_url = img_tag.get('src') if img_tag else None
                        
                        full_url = self.get_full_url(url_path)
                        
                        if name and full_url:
                            subcategories.append({
                                'name': name,
                                'url': full_url,
                                'image_url': image_url
                            })
                    except Exception as e:
                        print(f"Ошибка при обработке подкатегории: {e}")
                        continue
            
            return subcategories
            
        except Exception as e:
            print(f"Ошибка при парсинге подкатегорий: {e}")
            return []

    def parse_products_from_page(self, page_url, main_category, subcategory):
        """Парсит товары со страницы подкатегории"""
        print(f"Парсим товары со страницы: {page_url}")
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
                    print(f"Ошибка при обработке товара: {e}")
                    continue
            
            return products_data
            
        except Exception as e:
            print(f"Ошибка при парсинге страницы товаров: {e}")
            return []

    def parse_product_preview(self, form, main_category, subcategory):
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
            
            # Цена - исправленный парсинг
            price_block = form.find('div', class_='product-preview__price')
            price = None
            if price_block:
                price_cur = price_block.find('span', class_='product-preview__price-cur')
                if price_cur:
                    price = price_cur.text.strip()
            
            # Изображение - исправленный парсинг
            image_url = None
            img_tag = form.find('img')
            if img_tag:
                # Пробуем разные атрибуты
                image_url = (img_tag.get('src') or 
                           img_tag.get('data-src') or 
                           img_tag.get('data-lazy'))
            
            # Наличие
            available_block = form.find('div', class_='product-preview__available')
            available = available_block.text.strip() if available_block else None
            
            # Формируем категории как плоский массив
            categories = [main_category, subcategory]
            
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
            print(f"Ошибка при парсинге превью товара: {e}")
            return None

    def parse_product_details(self, product_url):
        """Парсит детальную информацию о товаре"""
        print(f"Парсим детали товара: {product_url}")
        try:
            response = self.session.get(product_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Основная форма товара
            product_form = soup.find('form', class_='product')
            if not product_form:
                return {}
            
            details = {}
            
            # Название
            title_block = product_form.find('h1', class_='product__title')
            details['name'] = title_block.text.strip() if title_block else None
            
            # Цена - исправленный парсинг для детальной страницы
            price = None
            price_block = product_form.find('div', class_='product__price')
            if price_block:
                price_cur = price_block.find('span', class_='product__price-cur')
                if price_cur:
                    price = price_cur.text.strip()
            
            details['price'] = price
            
            # Все изображения - исправленный парсинг
            images = []
            
            # Пробуем найти в основном галерее
            gallery_main = product_form.find('div', class_='product__gallery-main')
            if gallery_main:
                img_tags = gallery_main.find_all('img')
                for img in img_tags:
                    src = (img.get('src') or 
                          img.get('data-src') or 
                          img.get('data-lazy'))
                    if src and src not in images:
                        images.append(src)
            
            # Пробуем найти в скрытом блоке со всеми изображениями
            gallery_all = product_form.find('div', class_='js-product-all-images')
            if gallery_all:
                img_tags = gallery_all.find_all('img')
                for img in img_tags:
                    src = (img.get('src') or 
                          img.get('data-src') or 
                          img.get('data-lazy'))
                    if src and src not in images:
                        images.append(src)
            
            details['images'] = images
            
            # Основное изображение (первое)
            details['main_image'] = images[0] if images else None
            
            # Характеристики
            properties = {}
            properties_block = product_form.find('div', class_='product__properties-items')
            if properties_block:
                property_items = properties_block.find_all('div', class_='product__property')
                for item in property_items:
                    name_div = item.find('div', class_='product__property-name')
                    value_div = item.find('div', class_='product__property-value')
                    if name_div and value_div:
                        prop_name = name_div.text.strip().rstrip(':')
                        prop_value = value_div.text.strip()
                        properties[prop_name] = prop_value
            details['properties'] = properties
            
            # Описание
            description_block = product_form.find('div', class_='product__short-description')
            if description_block:
                # Убираем HTML теги для чистого текста
                description_text = description_block.get_text(strip=True)
                details['description'] = description_text
            else:
                details['description'] = None
            
            # Варианты (если есть)
            variants = []
            variants_block = product_form.find('div', class_='product__variants')
            if variants_block:
                option_selectors = variants_block.find_all('div', class_='option')
                for option in option_selectors:
                    option_label = option.find('label', class_='option-label')
                    if option_label:
                        option_name = option_label.text.strip()
                        option_values = []
                        value_buttons = option.find_all('button', class_='option-value')
                        for btn in value_buttons:
                            option_values.append(btn.text.strip())
                        variants.append({
                            'option': option_name,
                            'values': option_values
                        })
            details['variants'] = variants
            
            return details
            
        except Exception as e:
            print(f"Ошибка при парсинге деталей товара: {e}")
            return {}

    def handle_pagination(self, subcategory_url, main_category, subcategory):
        """Обрабатывает пагинацию в подкатегории"""
        all_products = []
        page = 1
        
        while True:
            if page == 1:
                current_url = subcategory_url
            else:
                # Добавляем параметр page к URL
                parsed_url = urlparse(subcategory_url)
                if '?' in subcategory_url:
                    current_url = f"{subcategory_url}&page={page}"
                else:
                    current_url = f"{subcategory_url}?page={page}"
            
            print(f"Обрабатываем страницу {page}: {current_url}")
            
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

    def parse_all_products(self, categories_with_subcategories):
        """Парсит все товары из всех подкатегорий"""
        all_products_dict = {}  # Используем dict для объединения товаров по ID
        
        for category in categories_with_subcategories:
            category_name = category['name']
            subcategories = category.get('subcategories', [])
            
            for subcategory in subcategories:
                subcategory_name = subcategory['name']
                subcategory_url = subcategory['url']
                
                print(f"\nОбрабатываем: {category_name} -> {subcategory_name}")
                
                # Парсим товары из подкатегории (с пагинацией)
                products = self.handle_pagination(subcategory_url, category_name, subcategory_name)
                
                # Обновляем информацию о товарах
                for product in products:
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
                        # Новый товар, парсим детали
                        time.sleep(1)  # Задержка между запросами к товарам
                        details = self.parse_product_details(product['url'])
                        
                        # Объединяем данные
                        full_product_data = {**product, **details}
                        all_products_dict[product_id] = full_product_data
        
        return list(all_products_dict.values())

    def save_to_json(self, data, filename):
        """Сохраняет данные в JSON файл"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Данные сохранены в {filename}")

def main():
    parser = LaudLinkParser()
    
    print("Начинаем парсинг сайта laudlink.ru...")
    
    # 1. Парсим основные категории
    categories = parser.parse_categories()
    print(f"Найдено основных категорий: {len(categories)}")
    
    # 2. Парсим подкатегории для каждой категории
    categories_with_subcategories = []
    for category in categories:
        print(f"Обрабатываем категорию: {category['name']}")
        subcategories = parser.parse_subcategories(category['url'])
        category['subcategories'] = subcategories
        categories_with_subcategories.append(category)
        time.sleep(1)  # Задержка между категориями
    
    # Сохраняем структуру категорий
    parser.save_to_json(categories_with_subcategories, 'categories_structure.json')
    
    # 3. Парсим все товары
    print("\nНачинаем парсинг товаров...")
    all_products = parser.parse_all_products(categories_with_subcategories)
    
    # 4. Сохраняем товары
    parser.save_to_json(all_products, 'all_products.json')
    
    # Статистика
    total_products = len(all_products)
    total_categories = len(categories_with_subcategories)
    total_subcategories = sum(len(cat['subcategories']) for cat in categories_with_subcategories)
    
    print(f"\nПарсинг завершен!")
    print(f"Обработано:")
    print(f"- Категорий: {total_categories}")
    print(f"- Подкатегорий: {total_subcategories}")
    print(f"- Товаров: {total_products}")

if __name__ == "__main__":
    main()