# shop/management/commands/import_laudlink_all.py
from django.core.management.base import BaseCommand
from main.services.laudlink_adapter import LaudLinkAdapter

class Command(BaseCommand):
    help = 'Полный импорт категорий и товаров из LaudLink'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'categories_json',
            type=str,
            help='Путь к JSON файлу с категориями'
        )
        parser.add_argument(
            'products_json', 
            type=str,
            help='Путь к JSON файлу с товарами'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Ограничить количество товаров'
        )
    
    def handle(self, *args, **options):
        categories_file = options['categories_json']
        products_file = options['products_json']
        limit = options.get('limit')
        
        self.stdout.write("=== ПОЛНЫЙ ИМПОРТ LAUDLINK ===")
        
        # 1. Импорт категорий
        self.stdout.write("\n1. ИМПОРТ КАТЕГОРИЙ")
        categories_result = LaudLinkAdapter.import_categories_from_json(categories_file)
        
        if categories_result:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Категории импортированы: {categories_result['created']} создано, "
                    f"{categories_result['updated']} обновлено"
                )
            )
        else:
            self.stdout.write(self.style.ERROR("❌ Не удалось импортировать категории"))
            return
        
        # 2. Импорт товаров
        self.stdout.write("\n2. ИМПОРТ ТОВАРОВ")
        products_result = LaudLinkAdapter.import_products_from_json(products_file, limit)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Товары импортированы: {products_result['created']} создано, "
                f"{products_result['updated']} обновлено"
            )
        )
        
        if products_result['errors']:
            self.stdout.write(self.style.WARNING(f"Ошибки при импорте: {len(products_result['errors'])}"))
        
        self.stdout.write(self.style.SUCCESS("\n✅ Полный импорт завершен!"))