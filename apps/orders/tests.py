from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User, CafeProfile
from .models import Order


class OrderListFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='kopikita', email='owner@kopikita.id',
            password='pw12345!', role='cafe',
        )
        CafeProfile.objects.create(
            user=self.user, cafe_name='Kopi Kita', city='Bandung',
            province='Jawa Barat', postal_code='40111',
        )
        self.client.force_login(self.user)

    def _make(self, n, status):
        for i in range(n):
            Order.objects.create(
                cafe=self.user, order_number=f'{status}-{i}',
                shipping_address='Jl. Mawar 1', shipping_cost=0,
                subtotal=10000, total_amount=10000, status=status,
            )

    def test_counts_per_group(self):
        self._make(2, 'PENDING')
        self._make(3, 'DELIVERED')
        self._make(1, 'CANCELLED')
        resp = self.client.get(reverse('order_list'))
        counts = resp.context['counts']
        self.assertEqual(counts['all'], 6)
        self.assertEqual(counts['pending'], 2)
        self.assertEqual(counts['done'], 3)
        self.assertEqual(counts['cancelled'], 1)
        self.assertEqual(counts['process'], 0)

    def test_status_filter(self):
        self._make(2, 'PENDING')
        self._make(3, 'DELIVERED')
        resp = self.client.get(reverse('order_list'), {'status': 'done'})
        self.assertEqual(resp.context['active_status'], 'done')
        self.assertTrue(all(o.status == 'DELIVERED' for o in resp.context['orders']))
        self.assertEqual(len(resp.context['orders']), 3)

    def test_invalid_status_falls_back_to_all(self):
        self._make(1, 'PENDING')
        resp = self.client.get(reverse('order_list'), {'status': 'bogus'})
        self.assertEqual(resp.context['active_status'], 'all')

    def test_pagination_caps_at_ten(self):
        self._make(13, 'DELIVERED')
        resp = self.client.get(reverse('order_list'))
        self.assertEqual(len(resp.context['orders']), 10)
        self.assertEqual(resp.context['page_obj'].paginator.num_pages, 2)
        resp2 = self.client.get(reverse('order_list'), {'page': 2})
        self.assertEqual(len(resp2.context['orders']), 3)
