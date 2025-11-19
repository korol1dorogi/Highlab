from .cart import CartManager

def cart_quantity(request):
    """Добавляет количество товаров в корзине в контекст всех шаблонов"""
    try:
        cart_manager = CartManager(request)
        return {
            'cart_quantity': cart_manager.get_total_quantity()
        }
    except Exception as e:
        print(f"Error in cart_quantity context processor: {e}")
        return {'cart_quantity': 0}