from django.urls import path
from . import views

urlpatterns = [
    path('pay/<str:order_number>/', views.initiate_payment, name='initiate_payment'),
    path('webhook/', views.midtrans_webhook, name='midtrans_webhook'),
    path('success/<str:order_number>/', views.payment_success, name='payment_success'),
    path('credit-success/<str:order_number>/', views.credit_order_success, name='credit_order_success'),
    path('invoice/<int:invoice_id>/pay-online/', views.invoice_pay_online, name='invoice_pay_online'),
]
