from django.urls import path
from . import views

urlpatterns = [
    path('pay/<str:order_number>/', views.initiate_payment, name='initiate_payment'),
    path('webhook/', views.midtrans_webhook, name='midtrans_webhook'),
    path('success/<str:order_number>/', views.payment_success, name='payment_success'),
]
