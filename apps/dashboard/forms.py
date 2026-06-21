import uuid
from django import forms
from django.utils.text import slugify
from apps.catalog.models import Product


def _unique_slug(name):
    slug = slugify(name)
    if Product.objects.filter(slug=slug).exists():
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"
    return slug


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'description', 'price', 'unit',
                  'minimum_order', 'stock', 'image', 'is_active']

    def save(self, commit=True):
        product = super().save(commit=False)
        if not product.pk:
            product.slug = _unique_slug(product.name)
        if commit:
            product.save()
        return product
