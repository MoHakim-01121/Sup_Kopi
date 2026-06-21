from django.test import TestCase
from django.urls import reverse
from .models import User, CafeProfile


class AccountSidebarTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='kopikita', email='owner@kopikita.id',
            password='pw12345!', role='cafe', phone='0811',
        )
        CafeProfile.objects.create(
            user=self.user, cafe_name='Kopi Kita', address='Jl. Mawar 1',
            city='Bandung', province='Jawa Barat', postal_code='40111',
        )
        self.client.force_login(self.user)

    def test_profile_page_renders_sidebar_nav(self):
        resp = self.client.get(reverse('profile'))
        self.assertEqual(resp.status_code, 200)
        # sidebar nav links present
        self.assertContains(resp, 'href="/orders/"')
        self.assertContains(resp, 'href="/accounts/profile/"')
        # monogram = first two letters of cafe name, uppercased
        self.assertContains(resp, '>KO<')
        # active item marked on profile page
        self.assertContains(resp, 'acct-nav-item active')


class ProfileEditTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='kopikita', email='owner@kopikita.id',
            password='pw12345!', role='cafe', phone='0811',
        )
        self.profile = CafeProfile.objects.create(
            user=self.user, cafe_name='Kopi Kita', address='Jl. Mawar 1',
            city='Bandung', province='Jawa Barat', postal_code='40111',
        )
        self.client.force_login(self.user)

    def test_edit_page_renders(self):
        resp = self.client.get(reverse('profile_edit'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Kopi Kita')

    def test_edit_saves_changes(self):
        resp = self.client.post(reverse('profile_edit'), {
            'cafe_name': 'Kopi Nusantara', 'address': 'Jl. Melati 9',
            'city': 'Jakarta', 'province': 'DKI Jakarta',
            'postal_code': '10110', 'phone': '0822',
        })
        self.assertRedirects(resp, reverse('profile'))
        self.profile.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.profile.cafe_name, 'Kopi Nusantara')
        self.assertEqual(self.profile.city, 'Jakarta')
        self.assertEqual(self.user.phone, '0822')

    def test_email_and_username_not_editable(self):
        self.client.post(reverse('profile_edit'), {
            'cafe_name': 'X', 'address': 'Y', 'city': 'Z',
            'province': 'P', 'postal_code': '11111', 'phone': '0822',
            'username': 'hacked', 'email': 'hacked@evil.com',
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'kopikita')
        self.assertEqual(self.user.email, 'owner@kopikita.id')
