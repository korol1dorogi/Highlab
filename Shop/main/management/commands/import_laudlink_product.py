# shop/management/commands/import_laudlink_products.py
from django.core.management.base import BaseCommand
from main.services.laudlink_adapter import LaudLinkAdapter

class Command(BaseCommand):
    help = 'Импорт товаров из JSON файла парсера LaudLink'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help='Путь к JSON файлу с товарами (all_products_with_variants.json)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Ограничить количество импортируемых товаров (для тестирования)'
        )
    
    def handle(self, *args, **options):
        json_file = options['json_file']
        limit = options.get('limit')
        
        self.stdout.write(f"Начинаем импорт товаров из {json_file}...")
        if limit:
            self.stdout.write(f"Ограничение: {limit} товаров")
        
        results = LaudLinkAdapter.import_products_from_json(json_file, limit)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Импорт завершен: {results['created']} создано, "
                f"{results['updated']} обновлено, "
                f"{len(results['errors'])} ошибок"
            )
        )
        
        if results['errors']:
            self.stdout.write(self.style.ERROR("Ошибки:"))
            for error in results['errors'][:10]:
                self.stdout.write(self.style.ERROR(f"  - {error}"))