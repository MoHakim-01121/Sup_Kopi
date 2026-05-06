from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from .models import User, CafeProfile


class CafeRegistrationForm(UserCreationForm):
    cafe_name = forms.CharField(max_length=200)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))
    city = forms.CharField(max_length=100)
    province = forms.CharField(max_length=100)
    postal_code = forms.CharField(max_length=10)
    phone = forms.CharField(max_length=20, required=False)
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email, is_active=True).exists():
            raise forms.ValidationError('Email ini sudah terdaftar.')
        return email

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'cafe'
        user.phone = self.cleaned_data.get('phone', '')
        user.email = self.cleaned_data['email']
        user.save()
        CafeProfile.objects.create(
            user=user,
            cafe_name=self.cleaned_data['cafe_name'],
            address=self.cleaned_data['address'],
            city=self.cleaned_data['city'],
            province=self.cleaned_data['province'],
            postal_code=self.cleaned_data['postal_code'],
        )
        return user
