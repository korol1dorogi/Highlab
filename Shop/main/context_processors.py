from .models import Cart


def cart_quantity(request):
    """Количество товаров в корзине для всех шаблонов.

    ВАЖНО: только чтение — не создаём ни сессию, ни строку Cart. Иначе на каждый
    анонимный запрос (включая ботов) создавалась бы сессия и корзина, раздувая БД
    и ломая кэшируемость страниц. Корзину создаём лениво — только при добавлении товара.
    """
    try:
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).order_by('id').first()
        else:
            session_key = request.session.session_key
            cart = (
                Cart.objects.filter(session_key=session_key, user__isnull=True).order_by('id').first()
                if session_key else None
            )
        return {'cart_quantity': cart.total_quantity if cart else 0}
    except Exception:
        return {'cart_quantity': 0}
