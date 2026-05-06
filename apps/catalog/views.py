from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from .models import Category, Product

PRODUCT_PAGE_SIZE = 24

PRICE_PRESETS = {
    'low':  (None,   100_000),
    'mid':  (100_000, 500_000),
    'high': (500_000, None),
}


def home(request):
    categories = Category.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).filter(product_count__gt=0)

    featured = (
        Product.objects
        .filter(is_active=True)
        .select_related('category')
        .order_by('-created_at')[:8]
    )
    total_products = Product.objects.filter(is_active=True).count()

    return render(request, 'store/home.html', {
        'categories': categories,
        'featured_products': featured,
        'total_products': total_products,
    })


def product_list(request, slug=None):
    products = Product.objects.filter(is_active=True).select_related('category')
    categories = Category.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).filter(product_count__gt=0)

    category_slug = slug or request.GET.get('category', '')
    query        = request.GET.get('q', '')
    sort         = request.GET.get('sort', 'newest')
    in_stock     = request.GET.get('in_stock') == '1'
    price_preset = request.GET.get('price_preset', '')

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    else:
        category = None

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    if in_stock:
        products = products.filter(stock__gt=0)

    price_min_val, price_max_val = PRICE_PRESETS.get(price_preset, (None, None))
    if price_min_val is not None:
        products = products.filter(price__gte=price_min_val)
    if price_max_val is not None:
        products = products.filter(price__lte=price_max_val)

    sort_map = {
        'newest':     '-created_at',
        'price_asc':  'price',
        'price_desc': '-price',
        'name_asc':   'name',
    }
    products = products.order_by(sort_map.get(sort, '-created_at'))

    active_filter_count = sum([
        bool(category_slug),
        bool(query),
        bool(in_stock),
        bool(price_preset),
    ])

    paginator = Paginator(products, PRODUCT_PAGE_SIZE)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'store/product_list.html', {
        'products': page_obj,
        'page_obj': page_obj,
        'product_count': paginator.count,
        'categories': categories,
        'current_category': category,
        'query': query,
        'sort': sort,
        'in_stock': in_stock,
        'price_preset': price_preset,
        'active_filter_count': active_filter_count,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    related = []
    if product.category:
        related = (
            Product.objects
            .filter(is_active=True, category=product.category)
            .exclude(id=product.id)
            .select_related('category')
            .order_by('-created_at')[:4]
        )
    return render(request, 'store/product_detail.html', {
        'product': product,
        'related_products': related,
    })


def search_suggestions(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})
    products = (
        Product.objects
        .filter(is_active=True, name__icontains=q)
        .select_related('category')
        .values('name', 'slug', 'category__name')[:8]
    )
    results = [
        {
            'name': p['name'],
            'slug': p['slug'],
            'category': p['category__name'] or '',
        }
        for p in products
    ]
    return JsonResponse({'results': results})
