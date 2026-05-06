from apps.orders.models import Order


def pending_orders_count(request):
    if request.user.is_authenticated and request.user.is_any_supplier:
        count = Order.objects.filter(status='PENDING').count()
        return {'pending_orders_count': count}
    return {'pending_orders_count': 0}
