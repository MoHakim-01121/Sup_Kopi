from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from apps.accounts.decorators import cafe_required
from apps.catalog.models import Product
from apps.delivery.models import ShippingZone
from apps.orders.models import Order
from apps.orders.services import create_order_from_cart, InsufficientStockError
from apps.payments.models import CafeCredit, CreditInvoice
from .models import Cart, CartItem


@cafe_required
def cart_detail(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return render(request, 'store/cart.html', {'cart': cart})


@cafe_required
def cart_drawer(request):
    """Render isi mini-cart (slide-out drawer). Dipakai via fetch dari base_store."""
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return render(request, 'store/_cart_drawer.html', {'cart': cart})


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
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = item.quantity

    error = None
    if quantity < 1:
        item.delete()
    elif quantity < item.product.minimum_order:
        error = f'Minimum order {item.product.minimum_order} {item.product.unit}.'
    elif quantity > item.product.stock:
        error = f'Stok tidak cukup. Tersedia: {item.product.stock} {item.product.unit}.'
    else:
        item.quantity = quantity
        item.save()

    if is_ajax:
        cart = item.cart
        return JsonResponse({
            'ok': error is None,
            'message': error or '',
            'cart_count': cart.total_items,
        }, status=400 if error else 200)

    if error:
        messages.error(request, error)
    return redirect('/cart/')


@cafe_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart = item.cart
    item.delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'cart_count': cart.total_items})
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
    credit = getattr(request.user, 'credit_account', None)


    # Ingat zona pengiriman dari order terakhir → pre-select di checkout
    last_order = (
        Order.objects.filter(cafe=request.user, shipping_zone__isnull=False)
        .order_by('-created_at')
        .first()
    )
    last_zone_id = last_order.shipping_zone_id if last_order else None

    # Alasan kredit tidak bisa dipakai → ditampilkan & dinonaktifkan di checkout
    credit_block = None
    if credit and credit.is_enabled and credit.invoices.filter(status='OVERDUE').exists():
        credit_block = 'Ada tagihan yang sudah jatuh tempo. Lunasi dulu untuk memakai kredit.'

    if request.method == 'POST':
        zone_id = request.POST.get('shipping_zone')
        shipping_address = request.POST.get('shipping_address', '').strip()
        notes = request.POST.get('notes', '')
        payment_method = request.POST.get('payment_method', 'online')

        zone = ShippingZone.objects.filter(id=zone_id, is_active=True).first()
        if not shipping_address or not zone:
            messages.error(request, 'Lengkapi alamat dan pilih zona pengiriman yang valid.')
            return redirect('/cart/checkout/')

        # ── Validasi kredit DULU — sebelum order dibuat, stok dipotong, & keranjang dikosongkan ──
        if payment_method == 'credit':
            if not credit or not credit.is_enabled:
                messages.error(request, 'Fasilitas kredit tidak tersedia untuk akun ini.')
                return redirect('/cart/checkout/')
            order_total = cart.subtotal + zone.shipping_cost
            can, err = credit.can_place_order(order_total)
            if not can:
                messages.error(request, f'Kredit ditolak: {err}')
                return redirect('/cart/checkout/')

        try:
            order = create_order_from_cart(
                user=request.user,
                shipping_zone_id=zone.id,
                shipping_address=shipping_address,
                notes=notes,
            )
        except InsufficientStockError as e:
            messages.error(request, str(e))
            return redirect('/cart/')

        if payment_method == 'credit':
            due_date = timezone.now().date() + timedelta(days=credit.payment_term_days)
            CreditInvoice.objects.create(
                order=order,
                credit_account=credit,
                amount=order.total_amount,
                due_date=due_date,
            )
            order.status = 'CONFIRMED'
            order.confirmed_at = timezone.now()
            order.save()
            return redirect(f'/payments/credit-success/{order.order_number}/')

        return redirect(f'/payments/pay/{order.order_number}/')

    return render(request, 'store/checkout.html', {
        'cart': cart,
        'zones': zones,
        'profile': profile,
        'credit': credit,
        'credit_block': credit_block,
        'last_zone_id': last_zone_id,
    })

