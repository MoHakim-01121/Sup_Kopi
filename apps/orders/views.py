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


@cafe_required
def order_list(request):
    orders = (
        Order.objects
        .filter(cafe=request.user)
        .prefetch_related('items')
        .order_by('-created_at')
    )
    agg = Order.objects.filter(cafe=request.user).aggregate(total_spent=Sum('total_amount'))
    pending_count = Order.objects.filter(cafe=request.user, status='PENDING').count()
    return render(request, 'cafe/order_history.html', {
        'orders': orders,
        'total_spent': agg['total_spent'] or 0,
        'pending_count': pending_count,
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
