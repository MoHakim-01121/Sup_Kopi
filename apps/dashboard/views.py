import csv
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.text import slugify
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings as django_settings
from apps.accounts.decorators import supplier_required, supplier_admin_required, supplier_owner_required, cafe_required
from apps.accounts.models import SupplierStaff, StaffInvitation, User
from apps.orders.models import Order, OrderItem
from apps.catalog.models import Product, Category
from apps.payments.models import Payment
from apps.delivery.models import Delivery

PAGE_SIZE = 15
PAID_STATUSES = ['CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED']


def _filtered_orders(request):
    qs = Order.objects.select_related('cafe__cafe_profile').order_by('-created_at')
    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)
    return qs, status


def _filtered_deliveries(request):
    qs = Delivery.objects.select_related('order__cafe__cafe_profile').order_by('-created_at')
    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)
    return qs, status


def _unique_slug(name):
    slug = slugify(name)
    if Product.objects.filter(slug=slug).exists():
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"
    return slug


def _cafe_name(cafe):
    return getattr(getattr(cafe, 'cafe_profile', None), 'cafe_name', None) or cafe.email


@supplier_admin_required
def supplier_dashboard(request):
    today = timezone.now().date()
    week_start = today - timedelta(days=7)
    month_start = today.replace(day=1)

    orders_today = Order.objects.filter(created_at__date=today).count()
    orders_this_week = Order.objects.filter(created_at__date__gte=week_start).count()

    revenue_this_month = Order.objects.filter(
        status__in=PAID_STATUSES,
        created_at__date__gte=month_start,
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    pending_orders = Order.objects.filter(status='PENDING').count()
    pending_payments = Payment.objects.filter(status='PENDING').count()
    low_stock_count = Product.objects.filter(stock__lt=F('minimum_order'), is_active=True).count()

    top_products = (
        OrderItem.objects
        .values('product__name', 'product__id')
        .annotate(total_qty=Sum('quantity'), total_revenue=Sum('subtotal'))
        .order_by('-total_qty')[:5]
    )

    top_cafes = (
        Order.objects
        .filter(status__in=PAID_STATUSES)
        .values('cafe__cafe_profile__cafe_name', 'cafe__id')
        .annotate(order_count=Count('id'), total_spent=Sum('total_amount'))
        .order_by('-total_spent')[:5]
    )

    recent_orders = Order.objects.select_related('cafe__cafe_profile').order_by('-created_at')[:10]

    return render(request, 'supplier/dashboard.html', {
        'orders_today': orders_today,
        'orders_this_week': orders_this_week,
        'revenue_this_month': revenue_this_month,
        'pending_orders': pending_orders,
        'pending_payments': pending_payments,
        'low_stock_count': low_stock_count,
        'top_products': top_products,
        'top_cafes': top_cafes,
        'recent_orders': recent_orders,
    })


@supplier_admin_required
def order_management(request):
    orders, status_filter = _filtered_orders(request)
    paginator = Paginator(orders, PAGE_SIZE)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'supplier/order_management.html', {
        'orders': page,
        'page_obj': page,
        'status_filter': status_filter,
        'status_choices': Order.STATUS_CHOICES,
    })


@supplier_admin_required
def order_detail_supplier(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    delivery = getattr(order, 'delivery', None)
    payment = getattr(order, 'payment', None)
    cafe_orders = (
        Order.objects
        .filter(cafe=order.cafe)
        .exclude(id=order.id)
        .order_by('-created_at')[:5]
    )
    return render(request, 'supplier/order_detail.html', {
        'order': order,
        'delivery': delivery,
        'payment': payment,
        'cafe_orders': cafe_orders,
    })


@supplier_admin_required
def confirm_order(request, order_number):
    if request.method != 'POST':
        return redirect(f'/supplier/orders/{order_number}/')
    order = get_object_or_404(Order, order_number=order_number)
    if order.status == 'PENDING':
        order.status = 'CONFIRMED'
        order.save()
        messages.success(request, f'Order {order_number} berhasil dikonfirmasi.')
    else:
        messages.warning(request, 'Order tidak dalam status PENDING.')
    return redirect(request.POST.get('next', '/supplier/orders/'))


@supplier_admin_required
def bulk_confirm_orders(request):
    if request.method != 'POST':
        return redirect('/supplier/orders/')
    order_ids = request.POST.getlist('order_ids')
    if not order_ids:
        messages.warning(request, 'Tidak ada order yang dipilih.')
        return redirect('/supplier/orders/')
    updated = Order.objects.filter(id__in=order_ids, status='PENDING').update(status='CONFIRMED')
    messages.success(request, f'{updated} order berhasil dikonfirmasi.')
    return redirect('/supplier/orders/')


@supplier_admin_required
def export_orders_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders.csv"'
    writer = csv.writer(response)
    writer.writerow(['No. Order', 'Kafe', 'Tanggal', 'Status', 'Subtotal', 'Ongkir', 'Total'])
    orders, _ = _filtered_orders(request)
    for o in orders:
        writer.writerow([
            o.order_number,
            _cafe_name(o.cafe),
            o.created_at.strftime('%Y-%m-%d %H:%M'),
            o.get_status_display(),
            o.subtotal,
            o.shipping_cost,
            o.total_amount,
        ])
    return response


@supplier_admin_required
def export_deliveries_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="deliveries.csv"'
    writer = csv.writer(response)
    writer.writerow(['No. Order', 'Kafe', 'Kurir', 'No. Resi', 'Status', 'Estimasi Tiba'])
    deliveries, _ = _filtered_deliveries(request)
    for d in deliveries:
        writer.writerow([
            d.order.order_number,
            _cafe_name(d.order.cafe),
            d.courier_name,
            d.tracking_number,
            d.get_status_display(),
            d.estimated_delivery_date or '',
        ])
    return response


@supplier_admin_required
def product_management(request):
    products = Product.objects.select_related('category').order_by('-created_at')
    return render(request, 'supplier/product_management.html', {'products': products})


@supplier_admin_required
def add_product(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        Product.objects.create(
            name=name,
            slug=_unique_slug(name),
            category_id=request.POST.get('category') or None,
            description=request.POST.get('description'),
            price=request.POST.get('price'),
            unit=request.POST.get('unit'),
            minimum_order=request.POST.get('minimum_order', 1),
            stock=request.POST.get('stock', 0),
            image=request.FILES.get('image'),
            is_active=request.POST.get('is_active') == 'on',
        )
        messages.success(request, 'Produk berhasil ditambahkan.')
        return redirect('/supplier/products/')
    return render(request, 'supplier/product_form.html', {'categories': categories})


@supplier_admin_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    categories = Category.objects.all()
    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.category_id = request.POST.get('category') or None
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        product.unit = request.POST.get('unit')
        product.minimum_order = request.POST.get('minimum_order', 1)
        product.stock = request.POST.get('stock', 0)
        product.is_active = request.POST.get('is_active') == 'on'
        if request.FILES.get('image'):
            product.image = request.FILES.get('image')
        product.save()
        messages.success(request, 'Produk berhasil diupdate.')
        return redirect('/supplier/products/')
    return render(request, 'supplier/product_form.html', {
        'product': product,
        'categories': categories,
    })


@supplier_required
def delivery_list(request):
    deliveries, status_filter = _filtered_deliveries(request)
    paginator = Paginator(deliveries, PAGE_SIZE)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'supplier/delivery_list.html', {
        'deliveries': page,
        'page_obj': page,
        'status_filter': status_filter,
        'status_choices': Delivery.STATUS_CHOICES,
    })


@supplier_admin_required
def sales_chart_data(request):
    start_date = timezone.now().date() - timedelta(days=30)
    data = (
        Order.objects
        .filter(created_at__date__gte=start_date, status__in=PAID_STATUSES)
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(revenue=Sum('total_amount'), order_count=Count('id'))
        .order_by('date')
    )
    return JsonResponse({
        'labels': [str(d['date']) for d in data],
        'revenue': [float(d['revenue']) for d in data],
        'orders': [d['order_count'] for d in data],
    })


@cafe_required
def cafe_dashboard(request):
    cafe = request.user
    today = timezone.now().date()
    month_start = today.replace(day=1)

    recent_orders = Order.objects.filter(cafe=cafe).order_by('-created_at')[:5]
    monthly_spend = Order.objects.filter(
        cafe=cafe,
        status__in=PAID_STATUSES,
        created_at__date__gte=month_start,
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    active_orders = Order.objects.filter(
        cafe=cafe,
        status__in=['CONFIRMED', 'PROCESSING', 'SHIPPED'],
    )

    return render(request, 'cafe/dashboard.html', {
        'recent_orders': recent_orders,
        'monthly_spend': monthly_spend,
        'active_orders': active_orders,
    })


# ── Staff Management ──────────────────────────────────────────────────────────

@supplier_owner_required
def staff_list(request):
    staff = SupplierStaff.objects.select_related('user').order_by('-created_at')
    return render(request, 'supplier/staff_list.html', {'staff': staff})


@supplier_owner_required
def staff_invite(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', 'ADMIN')

        if not email:
            messages.error(request, 'Email tidak boleh kosong.')
            return render(request, 'supplier/staff_invite.html',
                          {'roles': SupplierStaff.ROLE_CHOICES})

        if User.objects.filter(email=email).exists():
            messages.error(request, f'Email "{email}" sudah terdaftar sebagai pengguna.')
            return render(request, 'supplier/staff_invite.html',
                          {'roles': SupplierStaff.ROLE_CHOICES})

        invitation = StaffInvitation.objects.create(
            email=email,
            role=role,
            invited_by=request.user,
        )

        setup_url = f"{django_settings.SITE_URL}/accounts/staff-setup/{invitation.token}/"
        role_label = dict(SupplierStaff.ROLE_CHOICES).get(role, role)

        send_mail(
            subject='Undangan bergabung ke Sup Kopi',
            message=(
                f'Kamu diundang sebagai {role_label} di Sup Kopi.\n\n'
                f'Klik link berikut untuk membuat akunmu (berlaku 48 jam):\n{setup_url}\n\n'
                f'Jika kamu tidak merasa diundang, abaikan email ini.'
            ),
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )

        messages.success(request, f'Undangan berhasil dikirim ke {email}.')
        return redirect('/supplier/staff/')

    return render(request, 'supplier/staff_invite.html',
                  {'roles': SupplierStaff.ROLE_CHOICES})


@supplier_owner_required
def staff_toggle(request, staff_id):
    if request.method != 'POST':
        return redirect('/supplier/staff/')
    staff = get_object_or_404(SupplierStaff, id=staff_id)
    staff.is_active = not staff.is_active
    staff.save()
    status = 'diaktifkan' if staff.is_active else 'dinonaktifkan'
    messages.success(request, f'Staff "{staff.user.username}" berhasil {status}.')
    return redirect('/supplier/staff/')


@supplier_owner_required
def staff_change_role(request, staff_id):
    if request.method != 'POST':
        return redirect('/supplier/staff/')
    staff = get_object_or_404(SupplierStaff, id=staff_id)
    new_role = request.POST.get('role')
    if new_role in dict(SupplierStaff.ROLE_CHOICES):
        staff.role = new_role
        staff.save()
        messages.success(request, f'Role "{staff.user.username}" diubah ke {staff.get_role_display()}.')
    return redirect('/supplier/staff/')
