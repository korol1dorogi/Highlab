# shop/management/commands/import_laudlink_categories.py
from django.core.management.base import BaseCommand
from main.services.laudlink_adapter import LaudLinkAdapter

class Command(BaseCommand):
    help = 'Импорт категорий из JSON файла парсера LaudLink'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help='Путь к JSON файлу с категориями (categories_structure.json)'
        )
    
    def handle(self, *args, **options):
        json_file = options['json_file']
        
        self.stdout.write(f"Начинаем импорт категорий из {json_file}...")
        
        result = LaudLinkAdapter.import_categories_from_json(json_file)
        
        if result:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Импорт категорий завершен: {result['created']} создано, "
                    f"{result['updated']} обновлено, всего {result['total']} категорий"
                )
            )
        else:
            self.stdout.write(self.style.ERROR("Не удалось импортировать категории"))