from django.db import models
from django.utils import timezone
import uuid


class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Menunggu Pembayaran'),
        ('CONFIRMED', 'Pembayaran Dikonfirmasi'),
        ('PROCESSING', 'Sedang Diproses'),
        ('SHIPPED', 'Dikirim'),
        ('DELIVERED', 'Terkirim'),
        ('CANCELLED', 'Dibatalkan'),
    ]

    cafe = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='orders',
        limit_choices_to={'role': 'cafe'}
    )
    order_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    shipping_zone = models.ForeignKey(
        'delivery.ShippingZone',
        on_delete=models.PROTECT,
        null=True
    )
    shipping_address = models.TextField()
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2)

    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            date_str = timezone.now().strftime('%Y%m%d')
            self.order_number = f"SKP-{date_str}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    @property
    def can_be_cancelled(self):
        return self.status == 'PENDING'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT)
    product_name = models.CharField(max_length=200)
    product_unit = models.CharField(max_length=50)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity}x {self.product_name}"
