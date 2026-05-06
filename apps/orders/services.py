from django.db import transaction
from django.db.models import F
from apps.cart.models import Cart
from apps.delivery.models import ShippingZone
from apps.catalog.models import Product
from .models import Order, OrderItem


class InsufficientStockError(Exception):
    pass


@transaction.atomic
def create_order_from_cart(user, shipping_zone_id, shipping_address, notes=''):
    cart = Cart.objects.get(user=user)

    if cart.total_items == 0:
        raise ValueError('Keranjang kosong.')

    # Lock product rows for the duration of this transaction to prevent overselling
    items = list(cart.items.select_related('product').select_for_update().all())

    for item in items:
        if item.product.stock < item.quantity:
            raise InsufficientStockError(
                f"Stok {item.product.name} tidak cukup. "
                f"Tersedia: {item.product.stock}, diminta: {item.quantity}"
            )

    shipping_zone = ShippingZone.objects.get(id=shipping_zone_id)
    subtotal = sum(item.product.price * item.quantity for item in items)
    total = subtotal + shipping_zone.shipping_cost

    order = Order.objects.create(
        cafe=user,
        shipping_zone=shipping_zone,
        shipping_address=shipping_address,
        shipping_cost=shipping_zone.shipping_cost,
        subtotal=subtotal,
        total_amount=total,
        notes=notes,
    )

    for item in items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            product_name=item.product.name,
            product_unit=item.product.unit,
            unit_price=item.product.price,
            quantity=item.quantity,
        )
        Product.objects.filter(id=item.product.id).update(
            stock=F('stock') - item.quantity
        )

    cart.items.all().delete()
    return order
