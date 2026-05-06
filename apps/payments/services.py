import midtransclient
from django.conf import settings


def get_snap_client():
    return midtransclient.Snap(
        is_production=settings.MIDTRANS_IS_PRODUCTION,
        server_key=settings.MIDTRANS_SERVER_KEY,
        client_key=settings.MIDTRANS_CLIENT_KEY,
    )


def create_snap_token(order, base_url='http://127.0.0.1:8000'):
    snap = get_snap_client()

    transaction_details = {
        'order_id': f"SKP-{order.id}-{order.order_number}",
        'gross_amount': int(order.total_amount),
    }

    item_details = []
    for item in order.items.all():
        item_details.append({
            'id': str(item.product.id),
            'price': int(item.unit_price),
            'quantity': item.quantity,
            'name': item.product_name[:50],
        })
    item_details.append({
        'id': 'SHIPPING',
        'price': int(order.shipping_cost),
        'quantity': 1,
        'name': f'Ongkir - {order.shipping_zone.name}',
    })

    customer_details = {
        'first_name': order.cafe.cafe_profile.cafe_name,
        'email': order.cafe.email,
        'phone': order.cafe.phone or '-',
    }

    transaction = snap.create_transaction({
        'transaction_details': transaction_details,
        'item_details': item_details,
        'customer_details': customer_details,
        'callbacks': {
            'finish': f"{base_url}/payments/success/{order.order_number}/",
        },
    })

    return transaction['token'], transaction['redirect_url']
