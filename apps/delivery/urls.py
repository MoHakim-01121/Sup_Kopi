from django.urls import path
from . import views

urlpatterns = [
    path('create/<str:order_number>/', views.create_delivery, name='create_delivery'),
    path('update/<str:order_number>/', views.update_delivery, name='update_delivery'),
    path('track/<str:order_number>/', views.track_delivery, name='track_delivery'),
]
