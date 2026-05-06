from django.db import models


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
