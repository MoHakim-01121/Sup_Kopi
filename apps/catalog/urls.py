from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('produk/', views.product_list, name='product_list'),
    path('produk/sugesti/', views.search_suggestions, name='search_suggestions'),
    path('kategori/<slug:slug>/', views.product_list, name='product_by_category'),
    path('produk/<slug:slug>/', views.product_detail, name='product_detail'),
]
