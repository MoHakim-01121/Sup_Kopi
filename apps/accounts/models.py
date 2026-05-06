import random
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    ROLE_CHOICES = [
        ('supplier', 'Supplier'),
        ('supplier_staff', 'Supplier Staff'),
        ('cafe', 'Cafe'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='cafe')
    phone = models.CharField(max_length=20, blank=True)

    @property
    def is_supplier(self):
        return self.role == 'supplier'

    @property
    def is_supplier_staff(self):
        return self.role == 'supplier_staff'

    @property
    def is_any_supplier(self):
        return self.role in ('supplier', 'supplier_staff')

    @property
    def is_cafe(self):
        return self.role == 'cafe'


class CafeProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cafe_profile'
    )
    cafe_name = models.CharField(max_length=200)
    address = models.TextField(default='', blank=True)
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.cafe_name


class SupplierStaff(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Admin Order'),
        ('LOGISTICS', 'Logistik'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='staff_profile'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='ADMIN')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_staff'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == 'ADMIN'

    @property
    def is_logistics(self):
        return self.role == 'LOGISTICS'


class StaffInvitation(models.Model):
    ROLE_CHOICES = SupplierStaff.ROLE_CHOICES

    email = models.EmailField()
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='ADMIN')
    token = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    invited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_invitations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"Invitation → {self.email} ({self.role})"

    @property
    def is_expired(self):
        return (timezone.now() - self.created_at).total_seconds() > 48 * 3600


class EmailOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"OTP for {self.user.username}"

    @property
    def is_expired(self):
        return (timezone.now() - self.created_at).total_seconds() > 600  # 10 menit

    @classmethod
    def generate(cls, user):
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        code = f"{random.randint(0, 999999):06d}"
        return cls.objects.create(user=user, code=code)
