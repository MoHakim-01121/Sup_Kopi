import json
import hashlib
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.utils import timezone
from apps.accounts.decorators import cafe_required
from apps.orders.models import Order
from .models import Payment
from .services import create_snap_token

logger = logging.getLogger(__name__)


@cafe_required
def initiate_payment(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, cafe=request.user)

    if order.status != 'PENDING':
        messages.error(request, 'Order ini tidak memerlukan pembayaran.')
        return redirect(f'/orders/{order_number}/')

    payment, created = Payment.objects.get_or_create(
        order=order,
        defaults={
            'midtrans_order_id': f"SKP-{order.id}-{order.order_number}",
            'amount': order.total_amount,
        }
    )

    if created or not payment.snap_token:
        base_url = request.build_absolute_uri('/').rstrip('/')
        token, redirect_url = create_snap_token(order, base_url)
        payment.snap_token = token
        payment.snap_redirect_url = redirect_url
        payment.save()

    return render(request, 'store/payment.html', {
        'order': order,
        'payment': payment,
        'client_key': settings.MIDTRANS_CLIENT_KEY,
        'is_production': settings.MIDTRANS_IS_PRODUCTION,
    })


@csrf_exempt
@require_POST
def midtrans_webhook(request):
    data = json.loads(request.body)

    order_id = data.get('order_id')
    status_code = data.get('status_code')
    gross_amount = data.get('gross_amount')
    signature_key = data.get('signature_key')

    raw_string = f"{order_id}{status_code}{gross_amount}{settings.MIDTRANS_SERVER_KEY}"
    expected_signature = hashlib.sha512(raw_string.encode()).hexdigest()

    if signature_key != expected_signature:
        return HttpResponse(status=403)

    try:
        payment = Payment.objects.get(midtrans_order_id=order_id)
    except Payment.DoesNotExist:
        return HttpResponse(status=404)

    transaction_status = data.get('transaction_status')
    fraud_status = data.get('fraud_status')
    order = payment.order

    if transaction_status in ('capture', 'settlement') and fraud_status == 'accept':
        payment.status = 'PAID'
        order.status = 'CONFIRMED'
        order.confirmed_at = timezone.now()
    elif transaction_status in ('cancel', 'deny'):
        payment.status = 'FAILED'
    elif transaction_status == 'expire':
        payment.status = 'EXPIRED'

    payment.midtrans_transaction_id = data.get('transaction_id', '')
    payment.payment_type = data.get('payment_type', '')
    payment.save()
    order.save()

    return HttpResponse(status=200)


@cafe_required
def payment_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, cafe=request.user)

    # Verify payment status directly with Midtrans (covers local dev where webhook can't reach localhost)
    if order.status == 'PENDING':
        try:
            payment = Payment.objects.get(order=order)
            from .services import get_snap_client
            snap = get_snap_client()
            result = snap.transactions.status(payment.midtrans_order_id)

            transaction_status = result.get('transaction_status')
            fraud_status = result.get('fraud_status', 'accept')

            if transaction_status in ('capture', 'settlement') and fraud_status == 'accept':
                payment.status = 'PAID'
                payment.midtrans_transaction_id = result.get('transaction_id', '')
                payment.payment_type = result.get('payment_type', '')
                payment.save()
                order.status = 'CONFIRMED'
                order.confirmed_at = timezone.now()
                order.save()
            elif transaction_status in ('cancel', 'deny'):
                payment.status = 'FAILED'
                payment.save()
            elif transaction_status == 'expire':
                payment.status = 'EXPIRED'
                payment.save()
        except Exception:
            logger.exception("Midtrans status check failed for order %s", order_number)

    return render(request, 'store/payment_success.html', {'order': order})
