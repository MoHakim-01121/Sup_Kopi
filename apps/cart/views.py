from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from apps.accounts.decorators import cafe_required
from apps.catalog.models import Product
from apps.delivery.models import ShippingZone
from apps.orders.services import create_order_from_cart, InsufficientStockError
from .models import Cart, CartItem


@cafe_required
def cart_detail(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return render(request, 'store/cart.html', {'cart': cart})


@cafe_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1

    if quantity < product.minimum_order:
        msg = f'Minimum order {product.minimum_order} {product.unit}.'
        if is_ajax:
            return JsonResponse({'ok': False, 'message': msg}, status=400)
        messages.error(request, msg)
        return redirect(f'/produk/{product.slug}/')

    if quantity > product.stock:
        msg = f'Stok tidak cukup. Tersedia: {product.stock} {product.unit}.'
        if is_ajax:
            return JsonResponse({'ok': False, 'message': msg}, status=400)
        messages.error(request, msg)
        return redirect(f'/produk/{product.slug}/')

    cart, _ = Cart.objects.get_or_create(user=request.user)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        item.quantity += quantity
        if item.quantity > product.stock:
            item.quantity = product.stock
    else:
        item.quantity = quantity
    item.save()

    msg = f'{product.name} berhasil ditambahkan ke keranjang.'
    if is_ajax:
        return JsonResponse({'ok': True, 'message': msg, 'cart_count': cart.total_items})

    messages.success(request, msg)
    next_url = request.META.get('HTTP_REFERER') or '/produk/'
    return redirect(next_url)


@cafe_required
def update_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = item.quantity

    if quantity < 1:
        item.delete()
    elif quantity < item.product.minimum_order:
        messages.error(request, f'Minimum order {item.product.minimum_order} {item.product.unit}.')
    elif quantity > item.product.stock:
        messages.error(request, f'Stok tidak cukup. Tersedia: {item.product.stock} {item.product.unit}.')
    else:
        item.quantity = quantity
        item.save()

    return redirect('/cart/')


@cafe_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    messages.success(request, 'Item dihapus dari keranjang.')
    return redirect('/cart/')


@cafe_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    if cart.total_items == 0:
        messages.error(request, 'Keranjang kosong.')
        return redirect('/cart/')

    zones = ShippingZone.objects.filter(is_active=True)
    profile = request.user.cafe_profile

    if request.method == 'POST':
        zone_id = request.POST.get('shipping_zone')
        shipping_address = request.POST.get('shipping_address', '').strip()
        notes = request.POST.get('notes', '')

        if not zone_id or not shipping_address:
            messages.error(request, 'Lengkapi alamat dan pilih zona pengiriman.')
        else:
            try:
                order = create_order_from_cart(
                    user=request.user,
                    shipping_zone_id=zone_id,
                    shipping_address=shipping_address,
                    notes=notes,
                )
                return redirect(f'/payments/pay/{order.order_number}/')
            except InsufficientStockError as e:
                messages.error(request, str(e))
                return redirect('/cart/')

    return render(request, 'store/checkout.html', {
        'cart': cart,
        'zones': zones,
        'profile': profile,
    })