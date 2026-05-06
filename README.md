# SupKopi

Platform B2B supplier kopi — menghubungkan supplier dengan kafe. Dibangun dengan Django 6.

## Fitur

- Katalog produk kopi dengan manajemen stok
- Keranjang & checkout untuk kafe
- Pembayaran via Midtrans
- Dashboard supplier (manajemen produk, pesanan, pengiriman)
- Login Google OAuth untuk kafe
- OTP email untuk supplier
- Manajemen staff supplier

next?
- fitur pengiriman yang lebih advance
- sales tracking (kunjungan, dll)

## Tech Stack

- **Backend**: Django 6.0.4
- **Database**: SQLite (development)
- **Payment**: Midtrans
- **Auth**: django-allauth (Google OAuth)
- **Static files**: Whitenoise

---

## Setup

### 1. Clone repo

```bash
git clone https://github.com/MoHakim-01121/Sup_Kopi.git
cd Sup_Kopi
```

### 2. Buat virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Buat file `.env`

Buat file `.env` di root project:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True

# Midtrans
MIDTRANS_SERVER_KEY=your-midtrans-server-key
MIDTRANS_CLIENT_KEY=your-midtrans-client-key
MIDTRANS_IS_PRODUCTION=False

# Google OAuth (opsional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Email (untuk OTP supplier)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=Sup Kopi <noreply@supkopi.com>

# URL
SITE_URL=http://localhost:8000
```

### 5. Migrasi database

```bash
python manage.py migrate
```

### 6. Buat superuser

```bash
python manage.py createsuperuser
```

### 7. Jalankan server

```bash
python manage.py runserver
```

Buka [http://localhost:8000](http://localhost:8000)

---

## Struktur Apps

| App | Fungsi |
|---|---|
| `accounts` | User model, login kafe & supplier, OTP, staff |
| `catalog` | Produk dan manajemen stok |
| `cart` | Keranjang belanja |
| `orders` | Pembuatan dan tracking pesanan |
| `payments` | Integrasi Midtrans |
| `delivery` | Manajemen pengiriman oleh supplier |
| `dashboard` | Dashboard supplier |
| `analytics` | Analitik penjualan |

---

## Konfigurasi Midtrans

1. Daftar di [midtrans.com](https://midtrans.com)
2. Ambil Server Key dan Client Key dari dashboard Midtrans
3. Untuk development gunakan key Sandbox dan set `MIDTRANS_IS_PRODUCTION=False`

## Konfigurasi Google OAuth (opsional)

1. Buka [Google Cloud Console](https://console.cloud.google.com)
2. Buat project baru → Enable Google+ API
3. Buat OAuth 2.0 credentials
4. Tambahkan `http://localhost:8000/accounts/google/login/callback/` ke Authorized redirect URIs
5. Masukkan Client ID dan Secret ke `.env`
6. Login ke admin Django, buka **Sites** → ubah domain ke `localhost:8000`
