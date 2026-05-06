from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from apps.accounts.decorators import supplier_required, cafe_required
from apps.orders.models import Order
from .models import Delivery


@supplier_required
def create_delivery(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)

    if order.status != 'CONFIRMED':
        messages.error(request, 'Order belum dikonfirmasi pembayarannya.')
        return redirect(f'/supplier/orders/{order_number}/')

    if hasattr(order, 'delivery'):
        messages.error(request, 'Delivery untuk order ini sudah dibuat.')
        return redirect(f'/supplier/orders/{order_number}/')

    if request.method == 'POST':
        courier_name = request.POST.get('courier_name')
        tracking_number = request.POST.get('tracking_number')
        notes = request.POST.get('notes', '')

        estimated_date = (
            timezone.now().date() +
            timedelta(days=order.shipping_zone.estimated_days_max)
        )

        Delivery.objects.create(
            order=order,
            courier_name=courier_name,
            tracking_number=tracking_number,
            notes=notes,
            status='SHIPPED',
            shipped_at=timezone.now(),
            estimated_delivery_date=estimated_date,
        )

        order.status = 'SHIPPED'
        order.save()

        messages.success(request, f'Pengiriman untuk order {order_number} berhasil dicatat.')
        return redirect(f'/supplier/orders/{order_number}/')

    return render(request, 'supplier/delivery_form.html', {'order': order})


@supplier_required
def update_delivery(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    delivery = get_object_or_404(Delivery, order=order)

    if request.method == 'POST':
        new_status = request.POST.get('status')

        if new_status == 'DELIVERED' and delivery.status != 'DELIVERED':
            delivery.status = 'DELIVERED'
            delivery.delivered_at = timezone.now()
            order.status = 'DELIVERED'
            order.save()
        elif new_status == 'SHIPPED' and delivery.status == 'PREPARING':
            delivery.status = 'SHIPPED'
            delivery.shipped_at = timezone.now()
            order.status = 'SHIPPED'
            order.save()

        delivery.save()
        messages.success(request, 'Status pengiriman diperbarui.')
        return redirect(f'/supplier/orders/{order_number}/')

    return render(request, 'supplier/update_delivery.html', {
        'order': order,
        'delivery': delivery,
    })


@cafe_required
def track_delivery(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, cafe=request.user)
    delivery = getattr(order, 'delivery', None)
    return render(request, 'store/track_delivery.html', {
        'order': order,
        'delivery': delivery,
    })
