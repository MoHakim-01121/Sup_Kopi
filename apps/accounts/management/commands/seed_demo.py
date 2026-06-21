"""
Seed data sintesis untuk demo & pengujian Sup Kopi.

Membuat: kategori, produk, zona pengiriman, akun supplier & kafe (+ profil),
fasilitas kredit, contoh order di berbagai status, serta tagihan kredit
(UNPAID / OVERDUE / PAID) untuk menguji alur checkout, pembayaran, dan kredit.

Idempotent — aman dijalankan berulang:
    python manage.py seed_demo
    python manage.py seed_demo --flush-demo   # hapus dulu order/invoice demo lalu seed ulang
"""

import urllib.request
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.models import User, CafeProfile
from apps.catalog.models import Category, Product
from apps.delivery.models import ShippingZone
from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment, CafeCredit, CreditInvoice

DEMO_PASSWORD = "demo12345"

CATEGORIES = [
    ("Biji Kopi", "Biji kopi sangrai grosir untuk kafe."),
    ("Susu & Dairy", "Susu, krim, dan produk dairy barista."),
    ("Sirup & Saus", "Sirup rasa dan saus untuk minuman."),
    ("Teh", "Daun teh dan bubuk untuk seduhan."),
    ("Packaging", "Cup, lid, sedotan, dan kemasan."),
    ("Peralatan", "Perlengkapan barista dan kedai."),
]

# (kategori, nama, harga, satuan, min_order, stok, deskripsi)
PRODUCTS = [
    ("Biji Kopi", "Biji Kopi Arabika Gayo Premium", 145000, "kg", 5, 120, "Arabika Gayo single origin, profil fruity & clean."),
    ("Biji Kopi", "Biji Kopi Robusta Lampung", 95000, "kg", 5, 200, "Robusta bold dengan body tebal, cocok untuk espresso."),
    ("Biji Kopi", "Biji Kopi Arabika Toraja", 160000, "kg", 5, 80, "Arabika Toraja, earthy dengan keasaman seimbang."),
    ("Biji Kopi", "House Blend Espresso", 120000, "kg", 5, 150, "Blend serbaguna untuk espresso & milk-based."),
    ("Susu & Dairy", "Susu UHT Full Cream 1L (12 pcs)", 185000, "karton", 1, 90, "Susu UHT full cream, satu karton isi 12 liter."),
    ("Susu & Dairy", "Whipping Cream 1L", 78000, "botol", 2, 70, "Krim kocok stabil untuk topping & pastry."),
    ("Susu & Dairy", "Oat Milk Barista 1L", 52000, "botol", 6, 110, "Oat milk barista grade, micro-foam halus."),
    ("Susu & Dairy", "Susu Evaporasi 410ml (24 pcs)", 165000, "karton", 1, 60, "Susu evaporasi untuk kopi susu gula aren."),
    ("Sirup & Saus", "Sirup Vanilla 1L", 95000, "botol", 2, 75, "Sirup vanilla premium, larut sempurna."),
    ("Sirup & Saus", "Sirup Caramel 1L", 95000, "botol", 2, 65, "Sirup caramel untuk latte & frappe."),
    ("Sirup & Saus", "Sirup Hazelnut 1L", 98000, "botol", 2, 50, "Sirup hazelnut aromatik."),
    ("Sirup & Saus", "Saus Cokelat 1kg", 88000, "botol", 2, 40, "Saus cokelat kental untuk mocha & topping."),
    ("Teh", "Teh Hitam Premium 500g", 65000, "pack", 2, 90, "Daun teh hitam pilihan untuk milk tea."),
    ("Teh", "Matcha Powder Grade A 1kg", 320000, "pack", 1, 30, "Bubuk matcha grade A, warna hijau pekat."),
    ("Packaging", "Paper Cup 12oz (1000 pcs)", 210000, "dus", 1, 100, "Paper cup 12oz food grade, satu dus 1000 pcs."),
    ("Packaging", "Paper Cup 16oz (1000 pcs)", 240000, "dus", 1, 85, "Paper cup 16oz untuk minuman besar."),
    ("Packaging", "Lid Dome 90mm (1000 pcs)", 130000, "dus", 1, 95, "Tutup dome 90mm untuk cup cold drink."),
    ("Packaging", "Paper Straw (2500 pcs)", 90000, "dus", 1, 70, "Sedotan kertas ramah lingkungan."),
    ("Peralatan", "Tamper Stainless 58mm", 175000, "pcs", 1, 25, "Tamper stainless steel 58mm presisi."),
    ("Peralatan", "Milk Jug 600ml", 95000, "pcs", 1, 40, "Pitcher susu stainless 600ml untuk latte art."),
]

# Kata kunci foto per produk (bahasa Inggris untuk loremflickr.com).
PRODUCT_IMAGE_KEYWORDS = {
    "Biji Kopi Arabika Gayo Premium": "arabica,coffee,beans",
    "Biji Kopi Robusta Lampung":      "robusta,coffee,beans",
    "Biji Kopi Arabika Toraja":       "coffee,beans,roasted",
    "House Blend Espresso":           "espresso,coffee,blend",
    "Susu UHT Full Cream 1L (12 pcs)": "milk,carton,dairy",
    "Whipping Cream 1L":              "whipping,cream,dairy",
    "Oat Milk Barista 1L":            "oat,milk,barista",
    "Susu Evaporasi 410ml (24 pcs)":  "evaporated,milk,can",
    "Sirup Vanilla 1L":               "vanilla,syrup,bottle",
    "Sirup Caramel 1L":               "caramel,syrup,bottle",
    "Sirup Hazelnut 1L":              "hazelnut,syrup,bottle",
    "Saus Cokelat 1kg":               "chocolate,sauce,bottle",
    "Teh Hitam Premium 500g":         "black,tea,leaves",
    "Matcha Powder Grade A 1kg":      "matcha,powder,green",
    "Paper Cup 12oz (1000 pcs)":      "paper,cup,coffee",
    "Paper Cup 16oz (1000 pcs)":      "paper,cup,large",
    "Lid Dome 90mm (1000 pcs)":       "coffee,lid,plastic",
    "Paper Straw (2500 pcs)":         "paper,straw,eco",
    "Tamper Stainless 58mm":          "coffee,tamper,barista",
    "Milk Jug 600ml":                 "milk,jug,latte,art",
}

# Fallback per kategori jika produk tidak ada di dict di atas.
CATEGORY_IMAGE_KEYWORDS = {
    "Biji Kopi":    "coffee,beans",
    "Susu & Dairy": "milk,dairy",
    "Sirup & Saus": "syrup,bottle",
    "Teh":          "tea,leaves",
    "Packaging":    "coffee,cup,paper",
    "Peralatan":    "barista,coffee,tools",
}

# (nama, deskripsi area, ongkir, hari_min, hari_max)
ZONES = [
    ("Jakarta", "DKI Jakarta dan sekitarnya", 15000, 1, 2),
    ("Jabodetabek", "Bogor, Depok, Tangerang, Bekasi", 25000, 2, 3),
    ("Bandung Raya", "Kota & Kabupaten Bandung", 40000, 2, 4),
    ("Luar Jawa", "Pengiriman ke luar Pulau Jawa", 75000, 4, 7),
]


class Command(BaseCommand):
    help = "Buat data sintesis (demo) untuk menguji checkout, pembayaran, dan kredit."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush-demo",
            action="store_true",
            help="Hapus order, payment, dan invoice demo lebih dulu sebelum seeding ulang.",
        )
        parser.add_argument(
            "--skip-images",
            action="store_true",
            help="Lewati pembuatan foto produk (berguna saat offline).",
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            if options["flush_demo"]:
                self._flush_demo()

            cats = self._seed_categories()
            products = self._seed_products(cats)
            if not options["skip_images"]:
                self._seed_images(products)
            zones = self._seed_zones()
            supplier, cafes = self._seed_users()
            self._seed_credit(cafes)
            self._seed_orders(cafes, products, zones)
            self._seed_credit_invoices(cafes, products, zones)

        self._summary(supplier, cafes, products, zones)

    # ── Kategori & Produk ──────────────────────────────────────────────
    def _seed_categories(self):
        cats = {}
        for name, desc in CATEGORIES:
            cat, _ = Category.objects.get_or_create(
                slug=slugify(name),
                defaults={"name": name, "description": desc},
            )
            cats[name] = cat
        self.stdout.write(f"  • {len(cats)} kategori")
        return cats

    def _seed_products(self, cats):
        products = {}
        for cat_name, name, price, unit, min_order, stock, desc in PRODUCTS:
            product, _ = Product.objects.get_or_create(
                slug=slugify(name),
                defaults={
                    "category": cats[cat_name],
                    "name": name,
                    "description": desc,
                    "price": Decimal(price),
                    "unit": unit,
                    "minimum_order": min_order,
                    "stock": stock,
                    "is_active": True,
                },
            )
            products[name] = product
        self.stdout.write(f"  • {len(products)} produk")
        return products

    # ── Foto produk ────────────────────────────────────────────────────
    def _seed_images(self, products):
        attached = skipped = 0
        for lock, product in enumerate(products.values(), start=1):
            if product.image:
                skipped += 1
                continue
            keywords = PRODUCT_IMAGE_KEYWORDS.get(
                product.name,
                CATEGORY_IMAGE_KEYWORDS.get(
                    product.category.name if product.category else "", "coffee"
                ),
            )
            data = self._fetch_photo(keywords, lock) or self._placeholder(product)
            product.image.save(f"{product.slug}.jpg", ContentFile(data), save=True)
            attached += 1
        msg = f"  - {attached} foto produk dibuat"
        if skipped:
            msg += f" ({skipped} sudah punya foto - dilewati)"
        self.stdout.write(msg)

    def _fetch_photo(self, keywords, lock):
        """Ambil foto dari Unsplash (keyword-based), fallback ke picsum jika gagal."""
        # Unsplash source: keyword sebagai query, lock sebagai seed deterministik
        kw_plus = keywords.replace(",", "+")
        for url in [
            f"https://source.unsplash.com/600x600/?{kw_plus}&sig={lock}",
            f"https://loremflickr.com/600/600/{keywords}?lock={lock}",
            f"https://picsum.photos/seed/{lock}/600/600",
        ]:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "seed-demo"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    if resp.status == 200:
                        return resp.read()
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"    gagal ({exc}) coba fallback..."))
        return None

    def _placeholder(self, product):
        """Placeholder lokal: gradient kategori + nama produk terbaca jelas."""
        import os
        from PIL import Image, ImageDraw, ImageFont

        # (warna_atas, warna_bawah, warna_teks, warna_aksen)
        schemes = {
            "Biji Kopi":    ((55, 32, 18), (95, 62, 38), (245, 225, 195), (196, 148, 96)),
            "Susu & Dairy": ((195, 180, 160), (235, 225, 210), (55, 45, 35), (160, 130, 95)),
            "Sirup & Saus": ((100, 50, 28), (155, 88, 55), (250, 230, 200), (230, 155, 80)),
            "Teh":          ((38, 60, 32), (72, 105, 60), (215, 240, 190), (140, 200, 90)),
            "Packaging":    ((65, 58, 50), (110, 100, 88), (240, 232, 220), (195, 178, 155)),
            "Peralatan":    ((28, 33, 42), (55, 65, 80), (210, 225, 245), (120, 155, 195)),
        }
        cat_name = product.category.name if product.category else ""
        top, bot, fg, accent = schemes.get(cat_name, ((45, 45, 52), (75, 75, 85), (235, 232, 228), (160, 155, 148)))

        SIZE = 600
        img = Image.new("RGB", (SIZE, SIZE))
        draw = ImageDraw.Draw(img)

        # Gradient vertikal atas → bawah
        for y in range(SIZE):
            t = y / (SIZE - 1)
            r = int(top[0] + (bot[0] - top[0]) * t)
            g = int(top[1] + (bot[1] - top[1]) * t)
            b = int(top[2] + (bot[2] - top[2]) * t)
            draw.line([(0, y), (SIZE, y)], fill=(r, g, b))

        # Strip aksen bawah
        draw.rectangle([0, SIZE - 8, SIZE, SIZE], fill=accent)

        # Lingkaran dekoratif besar di tengah atas
        cx, cy, r = SIZE // 2, 210, 130
        circ_col = tuple(min(255, c + 20) for c in bot)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=circ_col)
        draw.ellipse([cx - r + 4, cy - r + 4, cx + r - 4, cy + r - 4], outline=accent, width=2)

        # Cari font sistem Windows
        font_big = font_cat = None
        for fp in ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/arial.ttf"]:
            if os.path.exists(fp):
                try:
                    font_big = ImageFont.truetype(fp, 36)
                    font_cat = ImageFont.truetype(fp, 18)
                    break
                except Exception:
                    pass

        # Label kategori (kecil, di atas)
        if font_cat and cat_name:
            draw.text((SIZE // 2, 60), cat_name.upper(), fill=accent, font=font_cat, anchor="mm")

        # Nama produk — wrap di ~16 karakter lalu rata tengah
        words, line, lines = product.name.split(), "", []
        for w in words:
            trial = f"{line} {w}".strip()
            if len(trial) > 16 and line:
                lines.append(line)
                line = w
            else:
                line = trial
        if line:
            lines.append(line)

        line_h = 44 if font_big else 28
        text_y = 370 - (len(lines) * line_h) // 2
        for ln in lines:
            if font_big:
                draw.text((SIZE // 2, text_y), ln, fill=fg, font=font_big, anchor="mm")
            else:
                draw.text((SIZE // 2 - len(ln) * 4, text_y), ln, fill=fg)
            text_y += line_h

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=88)
        return buf.getvalue()

    def _seed_zones(self):
        zones = []
        for name, area, cost, dmin, dmax in ZONES:
            zone, _ = ShippingZone.objects.get_or_create(
                name=name,
                defaults={
                    "area_description": area,
                    "shipping_cost": Decimal(cost),
                    "estimated_days_min": dmin,
                    "estimated_days_max": dmax,
                    "is_active": True,
                },
            )
            zones.append(zone)
        self.stdout.write(f"  • {len(zones)} zona pengiriman")
        return zones

    # ── Akun ───────────────────────────────────────────────────────────
    def _make_user(self, username, email, role, **extra):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "role": role, **extra},
        )
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save()
        return user

    def _seed_users(self):
        supplier = self._make_user(
            "supplier", "supplier@supkopi.test", "supplier",
            is_staff=True, first_name="Admin", last_name="Supplier",
        )

        cafe_specs = [
            # username, email, cafe_name, city, province, postal
            ("kopikenangan", "kafe1@supkopi.test", "Kopi Kenangan Senopati", "Jakarta Selatan", "DKI Jakarta", "12190"),
            ("janjijiwa", "kafe2@supkopi.test", "Janji Jiwa Kemang", "Jakarta Selatan", "DKI Jakarta", "12730"),
            ("forecoffee", "kafe3@supkopi.test", "Fore Coffee Dago", "Bandung", "Jawa Barat", "40135"),
        ]
        cafes = {}
        for username, email, cafe_name, city, province, postal in cafe_specs:
            user = self._make_user(username, email, "cafe", phone="0812-0000-0000")
            CafeProfile.objects.get_or_create(
                user=user,
                defaults={
                    "cafe_name": cafe_name,
                    "address": f"Jl. {cafe_name.split()[-1]} No. 10",
                    "city": city,
                    "province": province,
                    "postal_code": postal,
                },
            )
            cafes[username] = user
        self.stdout.write(f"  • 1 supplier + {len(cafes)} kafe (+ profil)")
        return supplier, cafes

    # ── Kredit ─────────────────────────────────────────────────────────
    def _seed_credit(self, cafes):
        # kafe1: kredit aktif, limit besar; kafe2: kredit aktif tapi nanti punya tagihan OVERDUE
        CafeCredit.objects.get_or_create(
            cafe=cafes["kopikenangan"],
            defaults={"credit_limit": Decimal(10_000_000), "payment_term_days": 30, "is_enabled": True},
        )
        CafeCredit.objects.get_or_create(
            cafe=cafes["janjijiwa"],
            defaults={"credit_limit": Decimal(5_000_000), "payment_term_days": 14, "is_enabled": True},
        )
        # kafe3 sengaja tanpa kredit → menguji alur "online only"
        self.stdout.write("  • 2 fasilitas kredit (kafe3 tanpa kredit)")

    # ── Order ──────────────────────────────────────────────────────────
    def _create_order(self, cafe, zone, items_spec, status, days_ago=0, confirmed=False):
        subtotal = sum(p.price * qty for p, qty in items_spec)
        total = subtotal + zone.shipping_cost
        profile = getattr(cafe, "cafe_profile", None)
        addr = (
            f"{profile.address}, {profile.city}, {profile.province} {profile.postal_code}"
            if profile else "Alamat demo"
        )
        order = Order.objects.create(
            cafe=cafe,
            status=status,
            shipping_zone=zone,
            shipping_address=addr,
            shipping_cost=zone.shipping_cost,
            subtotal=subtotal,
            total_amount=total,
            notes="",
            confirmed_at=timezone.now() if confirmed else None,
        )
        for product, qty in items_spec:
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                product_unit=product.unit,
                unit_price=product.price,
                quantity=qty,
            )
        if days_ago:
            ts = timezone.now() - timedelta(days=days_ago)
            Order.objects.filter(pk=order.pk).update(created_at=ts)
        return order

    def _seed_orders(self, cafes, products, zones):
        cafe1 = cafes["kopikenangan"]
        if Order.objects.filter(cafe=cafe1).exists():
            self.stdout.write("  • order demo sudah ada — dilewati")
            return

        jakarta = zones[0]
        p = products

        # Berbagai status untuk menguji halaman riwayat & detail order
        self._create_order(cafe1, jakarta, [
            (p["Biji Kopi Arabika Gayo Premium"], 10),
            (p["Susu UHT Full Cream 1L (12 pcs)"], 3),
        ], status="DELIVERED", days_ago=24, confirmed=True)

        self._create_order(cafe1, jakarta, [
            (p["House Blend Espresso"], 8),
            (p["Sirup Caramel 1L"], 4),
            (p["Paper Cup 16oz (1000 pcs)"], 2),
        ], status="SHIPPED", days_ago=10, confirmed=True)

        self._create_order(cafe1, jakarta, [
            (p["Oat Milk Barista 1L"], 12),
            (p["Matcha Powder Grade A 1kg"], 1),
        ], status="PROCESSING", days_ago=4, confirmed=True)

        self._create_order(cafe1, jakarta, [
            (p["Biji Kopi Robusta Lampung"], 6),
        ], status="CONFIRMED", days_ago=2, confirmed=True)

        self._create_order(cafe1, jakarta, [
            (p["Paper Straw (2500 pcs)"], 3),
        ], status="CANCELLED", days_ago=6)

        # PENDING + Payment → bisa langsung uji halaman /payments/pay/
        pending = self._create_order(cafe1, jakarta, [
            (p["Sirup Vanilla 1L"], 4),
            (p["Whipping Cream 1L"], 6),
        ], status="PENDING", days_ago=0)
        Payment.objects.get_or_create(
            order=pending,
            defaults={
                "midtrans_order_id": f"SKP-{pending.id}-{pending.order_number}",
                "amount": pending.total_amount,
                "status": "PENDING",
            },
        )
        self.stdout.write("  • 6 order demo untuk kafe1 (termasuk 1 PENDING + Payment)")

    # ── Tagihan kredit ─────────────────────────────────────────────────
    def _seed_credit_invoices(self, cafes, products, zones):
        cafe1 = cafes["kopikenangan"]
        cafe2 = cafes["janjijiwa"]
        credit1 = CafeCredit.objects.get(cafe=cafe1)
        credit2 = CafeCredit.objects.get(cafe=cafe2)
        today = timezone.now().date()
        jakarta = zones[0]
        p = products

        if CreditInvoice.objects.filter(credit_account__in=[credit1, credit2]).exists():
            self.stdout.write("  • invoice kredit demo sudah ada — dilewati")
            return

        # kafe1 — invoice UNPAID (jatuh tempo ~18 hari lagi)
        o1 = self._create_order(cafe1, jakarta, [
            (p["Biji Kopi Arabika Toraja"], 5),
            (p["Lid Dome 90mm (1000 pcs)"], 2),
        ], status="CONFIRMED", days_ago=12, confirmed=True)
        CreditInvoice.objects.create(
            order=o1, credit_account=credit1, amount=o1.total_amount,
            due_date=today + timedelta(days=18), status="UNPAID",
        )

        # kafe1 — invoice PAID (riwayat lunas)
        o2 = self._create_order(cafe1, jakarta, [
            (p["Tamper Stainless 58mm"], 2),
        ], status="CONFIRMED", days_ago=40, confirmed=True)
        inv2 = CreditInvoice.objects.create(
            order=o2, credit_account=credit1, amount=o2.total_amount,
            due_date=today - timedelta(days=10), status="PAID",
            payment_method="ONLINE", paid_at=timezone.now() - timedelta(days=12),
        )

        # kafe2 — invoice OVERDUE (jatuh tempo 5 hari lalu) → memblokir kredit baru
        o3 = self._create_order(cafe2, jakarta, [
            (p["Biji Kopi Robusta Lampung"], 8),
            (p["Paper Cup 12oz (1000 pcs)"], 2),
        ], status="CONFIRMED", days_ago=20, confirmed=True)
        CreditInvoice.objects.create(
            order=o3, credit_account=credit2, amount=o3.total_amount,
            due_date=today - timedelta(days=5), status="OVERDUE",
        )
        self.stdout.write("  • 3 tagihan kredit (UNPAID, PAID, OVERDUE)")

    # ── Hapus data demo ────────────────────────────────────────────────
    def _flush_demo(self):
        demo_cafes = User.objects.filter(
            username__in=["kopikenangan", "janjijiwa", "forecoffee"]
        )
        orders = Order.objects.filter(cafe__in=demo_cafes)
        CreditInvoice.objects.filter(order__in=orders).delete()
        Payment.objects.filter(order__in=orders).delete()
        OrderItem.objects.filter(order__in=orders).delete()
        count = orders.count()
        orders.delete()
        self.stdout.write(self.style.WARNING(f"  flush: {count} order demo dihapus"))

    # ── Ringkasan ──────────────────────────────────────────────────────
    def _summary(self, supplier, cafes, products, zones):
        self.stdout.write(self.style.SUCCESS("\nData sintesis siap.\n"))
        self.stdout.write(f"Password semua akun demo: {DEMO_PASSWORD}\n")
        self.stdout.write("Akun:")
        self.stdout.write(f"  supplier     supplier@supkopi.test  (role supplier)")
        self.stdout.write(f"  kafe1        kafe1@supkopi.test     Kopi Kenangan — kredit aktif (limit 10jt)")
        self.stdout.write(f"  kafe2        kafe2@supkopi.test     Janji Jiwa — kredit aktif TAPI ada tagihan OVERDUE")
        self.stdout.write(f"  kafe3        kafe3@supkopi.test     Fore Coffee — tanpa kredit (online only)")
        self.stdout.write("\nUji cepat:")
        self.stdout.write("  - Login kafe1 -> checkout -> pilih 'Bayar Nanti (Kredit)' (sukses)")
        self.stdout.write("  - Login kafe2 -> checkout -> pilih kredit (ditolak: ada tagihan jatuh tempo)")
        self.stdout.write("  - Login kafe1 -> /cafe/invoices/ -> lihat UNPAID / PAID / utilisasi")
        self.stdout.write("  - Login kafe1 -> /orders/ -> order PENDING punya tombol 'Bayar Sekarang'")
