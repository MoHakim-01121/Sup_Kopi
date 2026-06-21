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
