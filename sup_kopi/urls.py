from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from apps.dashboard import views as views_dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('accounts/', include('allauth.urls')),
    path('', include('apps.catalog.urls')),
    path('cart/', include('apps.cart.urls')),
    path('orders/', include('apps.orders.urls')),
    path('payments/', include('apps.payments.urls')),
    path('supplier/', include('apps.dashboard.urls')),
    path('cafe/dashboard/', RedirectView.as_view(url='/orders/', permanent=True)),
    path('cafe/invoices/', views_dashboard.cafe_invoices, name='cafe_invoices'),
    path('cafe/invoices/<int:invoice_id>/', views_dashboard.cafe_invoices, name='cafe_invoice_detail'),
    path('cafe/invoices/<int:invoice_id>/upload/', views_dashboard.cafe_invoice_upload, name='cafe_invoice_upload'),
    path('cafe/invoices/<int:invoice_id>/pdf/', views_dashboard.cafe_invoice_pdf, name='cafe_invoice_pdf'),
    path('supplier/analytics/', include('apps.analytics.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
