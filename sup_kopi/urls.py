from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from apps.dashboard import views as views_dashboard


class _SuperuserOnlyAdminSite(admin.AdminSite):
    def has_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def login(self, request, extra_context=None):
        from django.shortcuts import render
        return render(request, '403.html', status=403)


admin.site.__class__ = _SuperuserOnlyAdminSite


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
