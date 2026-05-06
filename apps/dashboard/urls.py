from django.urls import path
from . import views

urlpatterns = [
    # Supplier
    path('dashboard/', views.supplier_dashboard, name='supplier_dashboard'),
    path('orders/', views.order_management, name='order_management'),
    path('orders/bulk-confirm/', views.bulk_confirm_orders, name='bulk_confirm_orders'),
    path('orders/export/', views.export_orders_csv, name='export_orders_csv'),
    path('orders/<str:order_number>/', views.order_detail_supplier, name='order_detail_supplier'),
    path('orders/<str:order_number>/confirm/', views.confirm_order, name='confirm_order'),
    path('products/', views.product_management, name='product_management'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('deliveries/', views.delivery_list, name='delivery_list'),
    path('deliveries/export/', views.export_deliveries_csv, name='export_deliveries_csv'),
    path('api/sales-chart/', views.sales_chart_data, name='sales_chart_data'),
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/invite/', views.staff_invite, name='staff_invite'),
    path('staff/<int:staff_id>/toggle/', views.staff_toggle, name='staff_toggle'),
    path('staff/<int:staff_id>/role/', views.staff_change_role, name='staff_change_role'),

    # Cafe
    path('cafe/dashboard/', views.cafe_dashboard, name='cafe_dashboard'),
]
