# Redesain Account Center — Pesanan, Tagihan, Profil Kafe

**Tanggal:** 2026-06-21
**Status:** Disetujui untuk perencanaan

## Tujuan

Merombak tiga halaman akun kafe — **Pesanan Saya** (`/orders/`), **Tagihan Kredit**
(`/cafe/invoices/`), dan **Profil Kafe** (`/accounts/profile/`) — menjadi satu
**Account Center** dengan sidebar navigasi bersama, bergaya minimalis-modern. Referensi
visual: account center Traveloka (sidebar + kartu profil), dengan rasa Linear/Vercel
(flat, hairline, label mono uppercase) yang dihangatkan ala Stripe/Notion (kartu rounded
lembut, shadow sangat halus, ikon dalam chip).

## Masalah desain saat ini

- `cafe/invoices.html` & `cafe/order_history.html` melanggar Linear design system:
  shadow berat (`0 10px 26px`, `0 2px 12px`), `translateY` hover, badge pill `r-xl`,
  blok hijau "reorder" yang ramai.
- `accounts/profile.html` terlalu polos: dua kartu info di kolom `col-md-6` ter-center,
  tanpa identitas/hirarki.
- Ketiga halaman berdiri sendiri tanpa navigasi akun yang konsisten.

## Bahasa visual bersama

Mengikuti `[[feedback-linear-design-system]]` dan `[[feedback-no-dot-eyebrow]]`, dengan
penyesuaian "hangat":

- **Kartu:** putih, radius ~14px, hairline `var(--co-hairline)`, **shadow istirahat
  sangat halus** `0 1px 3px rgba(0,0,0,.05)`. Hover hanya menggelapkan border. TIDAK ada
  shadow berat / `translateY`.
- **Header kartu:** chip ikon bulat beraksen (lingkaran terisi `var(--co-deep-green)`,
  ikon putih kecil) + judul + aksi opsional di kanan.
- **Mikro-label:** mono uppercase 10px `var(--co-muted)`; value rapi di kanan.
- **Status:** teks-pill halus (warna tenang), bukan kapsul mencolok.
- **Angka penting:** Space Grotesk, ukuran lega.
- **Eyebrow:** mono uppercase tanpa dot.

## Arsitektur: shell akun ber-sidebar

Buat **partial sidebar bersama** `templates/partials/_account_sidebar.html` yang
di-include ketiga halaman, di dalam grid 2 kolom. Navbar atas tetap. Tidak membuat base
template baru — cukup blok layout di tiap halaman yang memuat sidebar + slot konten,
agar perubahan terisolasi per halaman dan mudah ditinjau.

**Grid:** sidebar sticky ~240px + konten kanan (maks ~720px). Di ≤768px sidebar menjadi
strip menu horizontal yang bisa di-scroll di atas konten (kartu profil tetap di atas,
nav jadi baris tab).

### Kartu profil sidebar (atas)
- Monogram inisial dalam lingkaran lembut (inisial dari `cafe_profile.cafe_name`, fallback
  `username`).
- Nama kafe (Space Grotesk, tebal) + baris kecil abu **metode login**: Google jika
  `user.socialaccount_set.exists()`, selain itu "Email" jika ada email, selain itu "OTP".
- **Badge keanggotaan:** jika `user.credit_account.is_enabled` → pill gradient hangat
  `Tersedia Rp {available_credit} ›` yang nge-link ke `/cafe/invoices/`. Jika tidak →
  pill netral `Akun Kafe`.

### Menu nav (berikon)
Item: **Pesanan Saya** (`/orders/`), **Tagihan Kredit** (`/cafe/invoices/`, hanya jika
kredit aktif), **Profil Kafe** (`/accounts/profile/`), **Logout** (`/accounts/logout/`,
varian danger).
- Aktif (cocok `request.path`): latar solid `var(--co-deep-green)`, teks/ikon putih.
- Lain: ikon abu + teks gelap; hover latar abu sangat lembut.

## Per halaman (panel kanan)

### 1. Pesanan Saya (`cafe/order_history.html`)
- Judul "Pesanan Saya" + link ghost "Belanja Lagi".
- **Ringkasan tenang** sebagai satu baris: `N ORDER · Rp X BELANJA · N MENUNGGU BAYAR`,
  dipisah divider tipis, tanpa box (ganti `.stats-strip` berkotak).
- **Alert jatuh tempo** (jika `overdue_count`): banner tint merah lembut, ikon kecil —
  bukan blok mencolok.
- **Daftar order:** baris bersih per kartu — `#nomor` mono, tanggal & jumlah produk abu,
  total Space Grotesk, status teks-pill, aksi kontekstual (Bayar untuk PENDING; Pesan
  Lagi; Detail). Hilangkan item-strip berlatar abu; ringkasan item jadi satu baris muted.
- "Pesan lagi" pesanan terakhir jadi link halus, bukan blok hijau penuh.
- Empty state tetap, dirapikan ke gaya baru.

### 2. Tagihan Kredit (`cafe/invoices.html`)
- **Kartu ringkasan kredit:** angka **Tersedia** besar (Space Grotesk) sebagai fokus;
  Limit & Outstanding sebagai stat tenang; bar utilisasi diflatkan (tetap, tipis, kalem).
- **Daftar tagihan:** baris bersih — nomor mono, jumlah Space Grotesk, jatuh tempo dengan
  warna urgensi halus, status teks-pill. Tombol "Bayar Online" **flat** (buang
  coral+`translateY`, pakai aksen tenang). Aksi sekunder (Transfer manual, PDF) jadi link
  halus.

### 3. Profil Kafe (`accounts/profile.html`) — dapat di-edit
- Dua kartu bergrup: **Akun** (username, email, no. HP, role) dan **Kafe** (nama, alamat,
  kota, provinsi, kode pos) — tiap baris label kiri–value kanan, separator tipis.
- Header tiap kartu pakai chip ikon + tombol **Edit** halus di kanan.
- **Halaman/route edit baru:** `/accounts/profile/edit/` (`profile_edit`) dengan
  `ProfileEditForm` (User: `phone`; CafeProfile: `cafe_name`, `address`, `city`,
  `province`, `postal_code`). `username`, `email`, `role` read-only. Template
  `accounts/profile_edit.html` memakai shell + gaya form Linear (input 13px, padding
  7px 11px). Submit → simpan → redirect ke profil dengan toast sukses.

## Yang diubah / ditambah

**Template baru:**
- `templates/partials/_account_sidebar.html`
- `templates/accounts/profile_edit.html`

**Template diubah:**
- `templates/cafe/order_history.html`, `templates/cafe/invoices.html`,
  `templates/accounts/profile.html` — bungkus dengan shell + sidebar, terapkan gaya baru.

**Backend:**
- `apps/accounts/views.py` — tambah `profile_edit` view.
- `apps/accounts/forms.py` — tambah `ProfileEditForm` (User + CafeProfile).
- `apps/accounts/urls.py` — tambah route `profile/edit/`.

**Tidak berubah:** model, alur kredit/pembayaran, navbar atas.

## Di luar lingkup
- Tidak mengubah panel supplier.
- Tidak mengubah model database.
- Tidak menambah field profil baru.

## Kriteria sukses
- Ketiga halaman memakai sidebar akun yang sama dengan item aktif tersorot benar.
- Tidak ada shadow berat / `translateY` tersisa; kartu flat-hangat konsisten.
- Profil dapat di-edit dan tersimpan; field read-only tetap terlindungi.
- Responsif: sidebar menjadi strip menu di mobile.
- Konsisten dengan `[[feedback-linear-design-system]]` & `[[feedback-no-dot-eyebrow]]`.
