
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from apps.accounts.decorators import cafe_required
from apps.cart.models import Cart, CartItem
from .models import Order



@login_required
def order_detail(request, order_number):
    if request.user.is_cafe:
        order = get_object_or_404(Order, order_number=order_number, cafe=request.user)
    else:
        order = get_object_or_404(Order, order_number=order_number)
    return render(request, 'store/order_detail.html', {'order': order})


ORDER_STATUS_GROUPS = {
    'all': None,
    'pending': ['PENDING'],
    'process': ['CONFIRMED', 'PROCESSING', 'SHIPPED'],
    'done': ['DELIVERED'],
    'cancelled': ['CANCELLED'],
}


@cafe_required
def order_list(request):
    from django.db.models import Q, Count
    from django.utils import timezone
    from django.core.paginator import Paginator

    active = request.GET.get('status', 'all')
    if active not in ORDER_STATUS_GROUPS:
        active = 'all'

    base = Order.objects.filter(cafe=request.user)

    # Jumlah pesanan per grup status untuk badge tab
    raw = dict(base.values_list('status').annotate(c=Count('id')))
    counts = {
        key: (sum(raw.values()) if group is None else sum(raw.get(s, 0) for s in group))
        for key, group in ORDER_STATUS_GROUPS.items()
    }

    orders_qs = base.prefetch_related('items').order_by('-created_at')
    group = ORDER_STATUS_GROUPS[active]
    if group:
        orders_qs = orders_qs.filter(status__in=group)

    page_obj = Paginator(orders_qs, 10).get_page(request.GET.get('page'))
    last_order = base.order_by('-created_at').first()

    credit = getattr(request.user, 'credit_account', None)
    overdue_count = 0
    if credit and credit.is_enabled:
        overdue_count = credit.invoices.filter(
            Q(status='OVERDUE') | Q(status='UNPAID', due_date__lt=timezone.now().date())
        ).count()

    return render(request, 'cafe/order_history.html', {
        'page_obj': page_obj,
        'orders': page_obj.object_list,
        'counts': counts,
        'active_status': active,
        'has_any': bool(raw),
        'last_order': last_order,
        'overdue_count': overdue_count,
    })


@cafe_required
def cancel_order(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, cafe=request.user)
    if order.can_be_cancelled:
        order.status = 'CANCELLED'
        order.save()
        messages.success(request, 'Order berhasil dibatalkan.')
    else:
        messages.error(request, 'Order tidak dapat dibatalkan.')
    return redirect(f'/orders/{order.order_number}/')


@cafe_required
def reorder(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, cafe=request.user)
    cart, _ = Cart.objects.get_or_create(user=request.user)
    added = 0
    for item in order.items.select_related('product'):
        product = item.product
        if not product.is_active or not product.is_in_stock:
            continue
        qty = min(item.quantity, product.stock)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if created:
            cart_item.quantity = qty
        else:
            cart_item.quantity = min(cart_item.quantity + qty, product.stock)
        cart_item.save()
        added += 1
    if added:
        messages.success(request, f'{added} produk dari order {order_number} ditambahkan ke keranjang.')
    else:
        messages.warning(request, 'Semua produk dari order ini sudah tidak tersedia.')
    return redirect('/cart/')
