from apps.orders.models import Order
from apps.payments.models import CreditInvoice


def pending_orders_count(request):
    if request.user.is_authenticated and request.user.is_any_supplier:
        count = Order.objects.filter(status='PENDING').count()
        verifying = CreditInvoice.objects.filter(status='VERIFYING').count()
        return {
            'pending_orders_count': count,
            'verifying_count': verifying,
        }
    return {'pending_orders_count': 0, 'verifying_count': 0}
