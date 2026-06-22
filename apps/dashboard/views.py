import csv
import uuid
from decimal import Decimal
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
from apps.payments.models import Payment, CafeCredit, CreditInvoice

PAGE_SIZE = 15
PAID_STATUSES = ['CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED']


def _filtered_orders(request):
    qs = Order.objects.select_related('cafe__cafe_profile').order_by('-created_at')
    status = request.GET.get('status')
    q = request.GET.get('q', '').strip()
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(
            Q(order_number__icontains=q) |
            Q(cafe__cafe_profile__cafe_name__icontains=q) |
            Q(cafe__email__icontains=q)
        )
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

    top_products = list(
        OrderItem.objects
        .values('product__name', 'product__id')
        .annotate(total_qty=Sum('quantity'), total_revenue=Sum('subtotal'))
        .order_by('-total_qty')[:5]
    )
    max_qty = top_products[0]['total_qty'] if top_products else 0
    for p in top_products:
        p['pct'] = round(p['total_qty'] / max_qty * 100) if max_qty else 0

    top_cafes = list(
        Order.objects
        .filter(status__in=PAID_STATUSES)
        .values('cafe__cafe_profile__cafe_name', 'cafe__id')
        .annotate(order_count=Count('id'), total_spent=Sum('total_amount'))
        .order_by('-total_spent')[:5]
    )
    max_spent = top_cafes[0]['total_spent'] if top_cafes else 0
    for c in top_cafes:
        c['pct'] = round(float(c['total_spent']) / float(max_spent) * 100) if max_spent else 0

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
    payment = getattr(order, 'payment', None)
    cafe_orders = (
        Order.objects
        .filter(cafe=order.cafe)
        .exclude(id=order.id)
        .order_by('-created_at')[:5]
    )
    return render(request, 'supplier/order_detail.html', {
        'order': order,
        'payment': payment,
        'cafe_orders': cafe_orders,
    })


@supplier_admin_required
def update_order_status(request, order_number):
    """Ubah status order secara manual (menggantikan modul delivery)."""
    if request.method != 'POST':
        return redirect(f'/supplier/orders/{order_number}/')
    order = get_object_or_404(Order, order_number=order_number)
    new_status = request.POST.get('status')
    valid = {s for s, _ in Order.STATUS_CHOICES}
    if new_status not in valid:
        messages.error(request, 'Status tidak valid.')
        return redirect(f'/supplier/orders/{order_number}/')
    order.status = new_status
    if new_status == 'CONFIRMED' and not order.confirmed_at:
        order.confirmed_at = timezone.now()
    order.save()
    messages.success(request, f'Status order {order_number} diperbarui menjadi {order.get_status_display()}.')
    return redirect(f'/supplier/orders/{order_number}/')


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
def product_management(request):
    q = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    qs = Product.objects.select_related('category').order_by('-created_at')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if category_id:
        qs = qs.filter(category_id=category_id)
    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get('page'))
    categories = Category.objects.all()
    return render(request, 'supplier/product_management.html', {
        'products': page,
        'page_obj': page,
        'q': q,
        'category_id': category_id,
        'categories': categories,
    })


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


# ── Kredit Dagang — Supplier ──────────────────────────────────────────────────

@supplier_owner_required
def credit_management(request):
    """Daftar semua kafe beserta status kredit mereka."""
    cafes = User.objects.filter(role='cafe').select_related('cafe_profile', 'credit_account').order_by('cafe_profile__cafe_name')
    overdue_count = CreditInvoice.objects.filter(status='OVERDUE').count()
    verifying_count = CreditInvoice.objects.filter(status='VERIFYING').count()
    return render(request, 'supplier/credit_management.html', {
        'cafes': cafes,
        'overdue_count': overdue_count,
        'verifying_count': verifying_count,
    })


@supplier_owner_required
def credit_detail(request, cafe_id):
    """Detail kredit satu kafe + list semua invoice-nya."""
    cafe = get_object_or_404(User, id=cafe_id, role='cafe')
    credit, _ = CafeCredit.objects.get_or_create(cafe=cafe)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update':
            credit.credit_limit = request.POST.get('credit_limit', 0)
            credit.payment_term_days = request.POST.get('payment_term_days', 30)
            credit.is_enabled = request.POST.get('is_enabled') == 'on'
            credit.save()
            messages.success(request, 'Pengaturan kredit berhasil disimpan.')
        return redirect(f'/supplier/credits/{cafe_id}/')

    invoices = credit.invoices.select_related('order', 'confirmed_by').order_by('-created_at')
    return render(request, 'supplier/credit_detail.html', {
        'cafe': cafe,
        'credit': credit,
        'invoices': invoices,
    })


@supplier_admin_required
def invoice_verify(request, invoice_id):
    """Supplier review bukti transfer → konfirmasi atau tolak."""
    invoice = get_object_or_404(CreditInvoice, id=invoice_id, status='VERIFYING')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'confirm':
            invoice.confirm_manual(confirmed_by=request.user)
            messages.success(request, f'Invoice {invoice.order.order_number} dikonfirmasi lunas.')
            return redirect(f'/supplier/credits/{invoice.credit_account.cafe_id}/')
        elif action == 'reject':
            reason = request.POST.get('reason', '').strip()
            if not reason:
                messages.error(request, 'Alasan penolakan wajib diisi.')
            else:
                invoice.reject_proof(reason=reason)
                messages.warning(request, f'Bukti invoice {invoice.order.order_number} ditolak.')
                return redirect(f'/supplier/credits/{invoice.credit_account.cafe_id}/')

    return render(request, 'supplier/invoice_verify.html', {'invoice': invoice})


# ── Kredit Dagang — Kafe ──────────────────────────────────────────────────────

@cafe_required
def cafe_invoices(request, invoice_id=None):
    """Kafe melihat semua tagihan kredit mereka."""
    credit = getattr(request.user, 'credit_account', None)
    if not credit:
        messages.info(request, 'Kamu belum memiliki fasilitas kredit.')
        return redirect('/orders/')

    # Fallback untuk local dev: Midtrans tidak bisa kirim webhook ke localhost,
    # tapi query params sudah dikirim saat redirect finish.
    order_id = request.GET.get('order_id')
    transaction_status = request.GET.get('transaction_status')
    if order_id and transaction_status in ('settlement', 'capture'):
        try:
            inv = CreditInvoice.objects.get(
                midtrans_order_id=order_id,
                credit_account=credit,
                status__in=['UNPAID', 'OVERDUE'],
            )
            inv.mark_paid_online()
            messages.success(request, f'Pembayaran invoice {inv.order.order_number} berhasil dikonfirmasi.')
        except CreditInvoice.DoesNotExist:
            pass

    today = timezone.now().date()
    all_invoices = list(credit.invoices.select_related('order').all())
    for inv in all_invoices:
        inv.days_left = (inv.due_date - today).days

    def _bucket(inv):
        if inv.status == 'PAID':
            return 'paid'
        if inv.status == 'VERIFYING':
            return 'verifying'
        if inv.days_left <= 0:
            return 'attention'
        if inv.days_left <= 7:
            return 'week'
        return 'upcoming'

    buckets = {'attention': [], 'week': [], 'upcoming': [], 'verifying': [], 'paid': []}
    for inv in all_invoices:
        buckets[_bucket(inv)].append(inv)

    # Tagihan aktif: paling mendesak dulu. Selesai: terbaru dulu.
    for key in ('attention', 'week', 'upcoming'):
        buckets[key].sort(key=lambda i: i.days_left)
    buckets['verifying'].sort(key=lambda i: i.created_at, reverse=True)
    buckets['paid'].sort(key=lambda i: i.created_at, reverse=True)

    GROUP_META = [
        ('attention', 'Perlu Perhatian', 'danger'),
        ('week', 'Minggu Ini', 'warn'),
        ('upcoming', 'Mendatang', 'normal'),
        ('verifying', 'Menunggu Verifikasi', 'normal'),
        ('paid', 'Lunas', 'ok'),
    ]
    groups = [
        {'key': k, 'label': lbl, 'tone': tone, 'items': buckets[k]}
        for k, lbl, tone in GROUP_META if buckets[k]
    ]
    due_invoices = buckets['attention'] + buckets['week'] + buckets['upcoming']
    outstanding_count = len(due_invoices)
    total_due = sum((inv.amount for inv in due_invoices), Decimal('0'))
    overdue_count = len(buckets['attention'])
    overdue_total = sum((inv.amount for inv in buckets['attention']), Decimal('0'))
    next_due = min(due_invoices, key=lambda i: i.days_left) if due_invoices else None

    # Utilisasi kredit dalam persen (untuk track garis kredit)
    utilization = 0
    if credit.credit_limit and credit.credit_limit > 0:
        utilization = round(float(credit.outstanding_balance) / float(credit.credit_limit) * 100)

    return render(request, 'cafe/invoices.html', {
        'credit': credit,
        'groups': groups,
        'outstanding_count': outstanding_count,
        'total_due': total_due,
        'overdue_count': overdue_count,
        'overdue_total': overdue_total,
        'next_due': next_due,
        'has_any': bool(all_invoices),
        'utilization': utilization,
    })


@cafe_required
def cafe_invoice_pdf(request, invoice_id):
    """Generate PDF invoice kredit untuk kafe."""
    import traceback

    invoice = get_object_or_404(
        CreditInvoice,
        id=invoice_id,
        credit_account__cafe=request.user,
    )

    try:
        from io import BytesIO
        from django.template.loader import get_template
        from xhtml2pdf import pisa

        template = get_template('cafe/invoice_pdf.html')
        html = template.render({'invoice': invoice}, request)

        buffer = BytesIO()
        pisa.CreatePDF(html, dest=buffer, encoding='utf-8')
        buffer.seek(0)

        filename = f"invoice-{invoice.order.order_number}.pdf"
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
    except Exception as e:
        return HttpResponse(
            f"<pre>ERROR: {type(e).__name__}: {e}\n\n{traceback.format_exc()}</pre>",
            status=200
        )


@cafe_required
def cafe_invoice_upload(request, invoice_id):
    """Kafe upload bukti transfer untuk invoice UNPAID/OVERDUE."""
    invoice = get_object_or_404(
        CreditInvoice,
        id=invoice_id,
        credit_account__cafe=request.user,
        status__in=['UNPAID', 'OVERDUE'],
    )

    if request.method == 'POST':
        image = request.FILES.get('proof_image')
        note = request.POST.get('proof_note', '').strip()
        if not image:
            messages.error(request, 'File bukti wajib diupload.')
        else:
            invoice.upload_proof(image_file=image, note=note)
            messages.success(request, 'Bukti berhasil diupload. Menunggu verifikasi supplier.')
            return redirect('/cafe/invoices/')

    return render(request, 'cafe/invoice_upload.html', {'invoice': invoice})
