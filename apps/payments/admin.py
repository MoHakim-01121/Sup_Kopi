from django.contrib import admin
from .models import Payment, CafeCredit, CreditInvoice


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['midtrans_order_id', 'order', 'amount', 'status', 'payment_type', 'created_at']
    list_filter = ['status']
    search_fields = ['midtrans_order_id', 'order__order_number']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CafeCredit)
class CafeCreditAdmin(admin.ModelAdmin):
    list_display = ['cafe', 'credit_limit', 'payment_term_days', 'is_enabled', 'created_at']
    list_filter = ['is_enabled']
    search_fields = ['cafe__email', 'cafe__cafe_profile__cafe_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CreditInvoice)
class CreditInvoiceAdmin(admin.ModelAdmin):
    list_display = ['order', 'credit_account', 'amount', 'due_date', 'status', 'payment_method']
    list_filter = ['status', 'payment_method']
    search_fields = ['order__order_number']
    readonly_fields = ['created_at', 'proof_uploaded_at', 'paid_at']
