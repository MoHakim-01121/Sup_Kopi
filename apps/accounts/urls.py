from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_cafe, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('staff-setup/<str:token>/', views.staff_setup, name='staff_setup'),
    path('supplier/login/', views.supplier_login, name='supplier_login'),
    path('supplier/verify/', views.supplier_otp_verify, name='supplier_otp_verify'),
    path('supplier/resend/', views.supplier_otp_resend, name='supplier_otp_resend'),
]
