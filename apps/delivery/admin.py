from django.contrib import admin
from .models import ShippingZone


@admin.register(ShippingZone)
class ShippingZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'shipping_cost', 'estimated_days_min', 'estimated_days_max', 'is_active']
    list_editable = ['is_active']
