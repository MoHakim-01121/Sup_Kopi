from .models import Cart


def cart_count(request):
    if request.user.is_authenticated and hasattr(request.user, 'is_cafe') and request.user.is_cafe:
        try:
            cart = Cart.objects.get(user=request.user)
            return {'cart_count': cart.total_items}
        except Cart.DoesNotExist:
            pass
    return {'cart_count': 0}
