import json
from django.core.management.base import BaseCommand
from main.services.importer import import_multiple_products

class Command(BaseCommand):
    help = 'Импорт товаров из JSON файла'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help='Путь к JSON файлу с данными товаров'
        )
        parser.add_argument(
            '--category',
            type=str,
            help='Slug категории для импорта'
        )
    
    def handle(self, *args, **options):
        json_file = options['json_file']
        category_slug = options.get('category')
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                products_data = json.load(f)
            
            # Если файл содержит один товар, оборачиваем в список
            if isinstance(products_data, dict):
                products_data = [products_data]
            
            self.stdout.write(f"Начинаем импорт {len(products_data)} товаров...")
            
            results = import_multiple_products(products_data, category_slug)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Импорт завершен: {results['created']} создано, "
                    f"{results['updated']} обновлено, "
                    f"{len(results['errors'])} ошибок"
                )
            )
            
            if results['errors']:
                self.stdout.write(self.style.ERROR("Ошибки:"))
                for error in results['errors']:
                    self.stdout.write(self.style.ERROR(f"  - {error}"))
                    
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"Файл {json_file} не найден"))
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f"Ошибка парсинга JSON в файле {json_file}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Неожиданная ошибка: {str(e)}"))