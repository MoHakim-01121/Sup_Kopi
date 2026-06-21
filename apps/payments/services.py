import midtransclient
from django.conf import settings


def get_snap_client():
    return midtransclient.Snap(
        is_production=settings.MIDTRANS_IS_PRODUCTION,
        server_key=settings.MIDTRANS_SERVER_KEY,
        client_key=settings.MIDTRANS_CLIENT_KEY,
    )


def create_snap_transaction(order_id, amount, finish_url,
                            item_details=None, customer_details=None):
    """Generic Snap token creator. Dipakai untuk order biasa & invoice kredit.

    Returns (token, redirect_url).
    """
    snap = get_snap_client()

    payload = {
        'transaction_details': {
            'order_id': order_id,
            'gross_amount': int(amount),
        },
        'callbacks': {
            'finish': finish_url,
        },
    }
    if item_details:
        payload['item_details'] = item_details
    if customer_details:
        payload['customer_details'] = customer_details

    transaction = snap.create_transaction(payload)
    return transaction['token'], transaction['redirect_url']


def create_snap_token(order, base_url='http://127.0.0.1:8000'):
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

    return create_snap_transaction(
        order_id=f"SKP-{order.id}-{order.order_number}",
        amount=order.total_amount,
        finish_url=f"{base_url}/payments/success/{order.order_number}/",
        item_details=item_details,
        customer_details=customer_details,
    )


def create_invoice_snap_token(invoice, base_url='http://127.0.0.1:8000'):
    """Snap token untuk pelunasan invoice kredit. Mutates & saves invoice."""
    if not invoice.midtrans_order_id:
        invoice.midtrans_order_id = f"INV-{invoice.order.order_number}-{invoice.id}"

    token, redirect_url = create_snap_transaction(
        order_id=invoice.midtrans_order_id,
        amount=invoice.amount,
        finish_url=f"{base_url}/cafe/invoices/",
        customer_details={'email': invoice.credit_account.cafe.email},
    )
    invoice.snap_token = token
    invoice.snap_redirect_url = redirect_url
    invoice.save()
    return token, redirect_url
