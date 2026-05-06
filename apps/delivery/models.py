from django.db import models


class ShippingZone(models.Model):
    name = models.CharField(max_length=100)
    area_description = models.TextField()
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_days_min = models.PositiveIntegerField(default=1)
    estimated_days_max = models.PositiveIntegerField(default=3)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} (Rp {self.shipping_cost:,.0f})"

    @property
    def delivery_estimate_display(self):
        if self.estimated_days_min == self.estimated_days_max:
            return f"{self.estimated_days_min} hari kerja"
        return f"{self.estimated_days_min}-{self.estimated_days_max} hari kerja"


class Delivery(models.Model):
    STATUS_CHOICES = [
        ('PREPARING', 'Mempersiapkan Paket'),
        ('SHIPPED', 'Dalam Pengiriman'),
        ('DELIVERED', 'Terkirim'),
    ]

    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='delivery'
    )
    courier_name = models.CharField(max_length=100)
    tracking_number = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PREPARING')
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    estimated_delivery_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    proof_image = models.ImageField(upload_to='deliveries/proof/%Y/%m/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Delivery {self.order.order_number} - {self.status}"
