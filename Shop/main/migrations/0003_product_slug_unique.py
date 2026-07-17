from django.db import migrations, models


def dedupe_slugs(apps, schema_editor):
    """Перед включением unique=True делаем существующие slug уникальными.

    Товары с одинаковым slug (например, одинаковые названия из импорта) получают
    суффикс -<id>. Пустые slug — тоже (по названию/по id), чтобы не упасть на constraint.
    """
    Product = apps.get_model('main', 'Product')
    seen = set()
    for product in Product.objects.all().order_by('id').iterator():
        base = (product.slug or '').strip() or f'product-{product.pk}'
        slug = base
        if slug in seen:
            slug = f'{base}-{product.pk}'
        # На случай коллизии даже с суффиксом
        counter = 2
        while slug in seen:
            slug = f'{base}-{product.pk}-{counter}'
            counter += 1
        if slug != product.slug:
            product.slug = slug[:200]
            product.save(update_fields=['slug'])
        seen.add(slug)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_remove_orderitem_product'),
    ]

    operations = [
        migrations.RunPython(dedupe_slugs, noop),
        migrations.AlterField(
            model_name='product',
            name='slug',
            field=models.SlugField(db_index=True, max_length=200, unique=True, verbose_name='URL товара'),
        ),
    ]
