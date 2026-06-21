from decimal import Decimal
from django.db import models
from django.utils import timezone


class Payment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Menunggu Pembayaran'),
        ('PAID', 'Sudah Dibayar'),
        ('FAILED', 'Gagal'),
        ('EXPIRED', 'Kedaluwarsa'),
    ]

    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='payment'
    )
    midtrans_order_id = models.CharField(max_length=100, unique=True)
    midtrans_transaction_id = models.CharField(max_length=100, blank=True)
    payment_type = models.CharField(max_length=50, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    snap_token = models.CharField(max_length=255, blank=True)
    snap_redirect_url = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.midtrans_order_id} - {self.status}"


# ── Kredit Dagang ─────────────────────────────────────────────────────────────

class CafeCredit(models.Model):
    cafe = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='credit_account',
        limit_choices_to={'role': 'cafe'},
    )
    credit_limit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    payment_term_days = models.PositiveIntegerField(default=30)
    is_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        name = getattr(getattr(self.cafe, 'cafe_profile', None), 'cafe_name', None) or self.cafe.email
        return f"Kredit {name}"

    @property
    def outstanding_balance(self):
        return self.invoices.filter(
            status__in=['UNPAID', 'VERIFYING', 'OVERDUE']
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

    @property
    def available_credit(self):
        return self.credit_limit - self.outstanding_balance

    def can_place_order(self, order_amount):
        if not self.is_enabled:
            return False, "Fasilitas kredit tidak aktif."
        if self.invoices.filter(status='OVERDUE').exists():
            return False, "Ada tagihan yang sudah melewati jatuh tempo."
        if Decimal(str(order_amount)) > self.available_credit:
            return False, f"Melebihi limit kredit. Tersedia Rp {self.available_credit:,.0f}."
        return True, None


class CreditInvoice(models.Model):
    STATUS_CHOICES = [
        ('UNPAID',    'Belum Dibayar'),
        ('VERIFYING', 'Menunggu Verifikasi'),
        ('OVERDUE',   'Jatuh Tempo'),
        ('PAID',      'Lunas'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('MANUAL', 'Transfer Manual'),
        ('ONLINE', 'Bayar Online'),
    ]

    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='credit_invoice',
    )
    credit_account = models.ForeignKey(
        CafeCredit,
        on_delete=models.PROTECT,
        related_name='invoices',
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    due_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='UNPAID')

    # diisi saat pelunasan
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='confirmed_invoices',
    )

    # bukti transfer — manual only
    proof_image = models.ImageField(upload_to='invoices/proof/%Y/%m/', null=True, blank=True)
    proof_note = models.CharField(max_length=200, blank=True)
    proof_uploaded_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    # midtrans — online only
    snap_token = models.CharField(max_length=255, blank=True)
    snap_redirect_url = models.CharField(max_length=500, blank=True)
    midtrans_order_id = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['due_date']

    def __str__(self):
        return f"Invoice {self.order.order_number} — {self.get_status_display()}"

    @property
    def is_overdue(self):
        return self.status == 'UNPAID' and timezone.now().date() > self.due_date

    def upload_proof(self, image_file, note=''):
        self.proof_image = image_file
        self.proof_note = note
        self.proof_uploaded_at = timezone.now()
        self.status = 'VERIFYING'
        self.rejection_reason = ''
        self.save()

    def confirm_manual(self, confirmed_by):
        self.status = 'PAID'
        self.payment_method = 'MANUAL'
        self.paid_at = timezone.now()
        self.confirmed_by = confirmed_by
        self.save()

    def reject_proof(self, reason):
        self.status = 'UNPAID'
        self.proof_image = None
        self.proof_note = ''
        self.proof_uploaded_at = None
        self.rejection_reason = reason
        self.save()

    def mark_paid_online(self):
        self.status = 'PAID'
        self.payment_method = 'ONLINE'
        self.paid_at = timezone.now()
        self.save()
