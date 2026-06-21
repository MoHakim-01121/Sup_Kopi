# Account Center Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the three cafe account pages (Pesanan Saya, Tagihan Kredit, Profil Kafe) into one sidebar-based Account Center with a warm-minimal visual language, and make the profile editable.

**Architecture:** A shared template partial `_account_sidebar.html` carries the shell CSS (2-column grid, sidebar, soft cards) and the sidebar markup (profile card + credit badge + icon nav). Each of the three pages wraps its content in `.acct-layout`, includes the partial with an `active=` flag, and renders its panel content in `.acct-main`. A new `profile_edit` view/form/url/template adds editing. No model or navbar changes.

**Tech Stack:** Django templates, allauth (`socialaccount_set` reverse relation), existing CSS custom-property design tokens (`var(--co-*)`, `var(--r-*)`), Space Grotesk / JetBrains Mono / Inter fonts. Tests via `python manage.py test`.

## Global Constraints

- Visual rules (verbatim from `[[feedback-linear-design-system]]`): body 14px; buttons 9px 18px padding, `var(--r-sm)` radius, 13px; table/list rows 8-9px vertical padding, 13px; NO box-shadow on card hover (border-color change only); dropdown/popup shadow max `0 4px 12px rgba(0,0,0,0.08)`.
- Per spec, cards may carry ONE very soft resting shadow `0 1px 3px rgba(0,0,0,.05)`; the heavy `0 10px 26px` / `0 2px 12px` shadows and all `translateY` hover transforms currently in `invoices.html` and `order_history.html` MUST be removed.
- Eyebrow labels: mono uppercase, NO leading dot element (`[[feedback-no-dot-eyebrow]]`).
- Accent color is `var(--co-deep-green)`. Pay buttons use this flat accent — no coral, no transform.
- Use existing design tokens only; do not introduce new colors literally except gradients explicitly specified here.
- Indonesian UI copy throughout.
- All three pages extend `base_store.html` and keep the top navbar unchanged.

---

### Task 1: Shared account shell + sidebar partial

Creates the reusable sidebar (profile card, credit badge, icon nav) and all shell CSS. The partial derives everything from `user` + a passed `active` flag — no view changes needed. Login method is read via allauth's `socialaccount_set`.

**Files:**
- Create: `templates/partials/_account_sidebar.html`
- Modify: `apps/accounts/tests.py`

**Interfaces:**
- Produces: include contract `{% include 'partials/_account_sidebar.html' with active='orders' %}` where `active` ∈ {`orders`, `invoices`, `profile`}. Consumers must wrap it in `<div class="acct-layout"> … <div class="acct-main"> … </div></div>`. CSS classes produced for consumers: `.acct-layout`, `.acct-main`, `.acct-card`, `.acct-card-head`, `.acct-card-ico`, `.acct-card-title`, `.acct-card-action`, `.acct-card-body`, `.acct-row` (label/value), `.acct-eyebrow`, `.acct-h1`, `.acct-ghost-link`, `.acct-stat-line`, `.acct-banner`, `.acct-textpill` (+ `.is-warn`/`.is-ok`/`.is-danger`), `.acct-amount`, `.acct-btn` (+ `.solid`), `.acct-empty`.

- [ ] **Step 1: Write the failing test**

Add to `apps/accounts/tests.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.accounts.tests.AccountSidebarTests -v 2`
Expected: FAIL — profile page does not yet include the sidebar (`'>KK<'` / `acct-nav-item active` not found). (This passes fully only after Task 4 wires the profile page; for now expect the sidebar-specific assertions to fail.)

- [ ] **Step 3: Create the sidebar partial**

Create `templates/partials/_account_sidebar.html`:

```html
{% load static %}
<style>
/* ── Account shell ─────────────────────────────── */
.acct-layout{display:grid;grid-template-columns:240px 1fr;gap:24px;align-items:start;padding:8px 0 56px;}
.acct-main{min-width:0;max-width:760px;}

/* Sidebar */
.acct-side{position:sticky;top:80px;display:flex;flex-direction:column;gap:14px;}
.acct-profile{
    border:1px solid var(--co-hairline);border-radius:14px;background:var(--co-canvas);
    box-shadow:0 1px 3px rgba(0,0,0,.05);padding:16px;
}
.acct-id{display:flex;align-items:center;gap:11px;}
.acct-mono{
    width:42px;height:42px;border-radius:50%;flex-shrink:0;
    display:flex;align-items:center;justify-content:center;
    font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:15px;
    color:var(--co-deep-green);background:var(--co-pale-green);letter-spacing:.5px;
}
.acct-name{font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:14px;color:var(--co-primary);line-height:1.2;}
.acct-login{font-size:11px;color:var(--co-muted);margin-top:2px;display:flex;align-items:center;gap:5px;}
.acct-badge{
    display:flex;align-items:center;justify-content:space-between;gap:8px;
    margin-top:13px;padding:9px 12px;border-radius:10px;text-decoration:none;
    font-size:12px;font-weight:500;
    background:linear-gradient(100deg,#1b3b34,#2e5b4f);color:#fff;
    transition:filter .15s;
}
.acct-badge:hover{filter:brightness(1.08);color:#fff;}
.acct-badge.neutral{background:var(--co-stone);color:var(--co-ink);cursor:default;}
.acct-badge .ab-go{font-size:11px;opacity:.8;}

/* Nav */
.acct-nav{
    border:1px solid var(--co-hairline);border-radius:14px;background:var(--co-canvas);
    box-shadow:0 1px 3px rgba(0,0,0,.05);padding:6px;display:flex;flex-direction:column;gap:2px;
}
.acct-nav-item{
    display:flex;align-items:center;gap:11px;padding:9px 12px;border-radius:9px;
    font-size:13px;font-weight:500;color:var(--co-body-muted);text-decoration:none;
    transition:background .15s,color .15s;
}
.acct-nav-item i{width:16px;text-align:center;font-size:13px;color:var(--co-muted);transition:color .15s;}
.acct-nav-item:hover{background:var(--co-stone);color:var(--co-primary);}
.acct-nav-item:hover i{color:var(--co-primary);}
.acct-nav-item.active{background:var(--co-deep-green);color:#fff;}
.acct-nav-item.active i{color:#fff;}
.acct-nav-item.danger{color:var(--co-error);}
.acct-nav-item.danger i{color:var(--co-error);}
.acct-nav-item.danger:hover{background:var(--co-error-bg);color:var(--co-error);}
.acct-nav-sep{height:1px;background:var(--co-hairline);margin:5px 8px;}

/* ── Shared content primitives ─────────────────── */
.acct-eyebrow{font-family:'JetBrains Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:1.4px;color:var(--co-muted);}
.acct-h1{font-family:'Space Grotesk',sans-serif;font-size:1.5rem;font-weight:600;letter-spacing:-.02em;color:var(--co-primary);margin:3px 0 0;}
.acct-page-head{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:20px;}
.acct-ghost-link{font-size:12px;font-weight:500;color:var(--co-primary);text-decoration:none;border:1px solid var(--co-hairline);border-radius:var(--r-sm);padding:7px 13px;display:inline-flex;align-items:center;gap:6px;transition:border-color .15s,background .15s;}
.acct-ghost-link:hover{border-color:var(--co-primary);background:var(--co-stone);color:var(--co-primary);}

.acct-card{border:1px solid var(--co-hairline);border-radius:14px;background:var(--co-canvas);box-shadow:0 1px 3px rgba(0,0,0,.05);margin-bottom:14px;overflow:hidden;}
.acct-card-head{display:flex;align-items:center;gap:11px;padding:14px 18px;border-bottom:1px solid var(--co-hairline);}
.acct-card-ico{width:28px;height:28px;border-radius:8px;background:var(--co-deep-green);color:#fff;display:flex;align-items:center;justify-content:center;font-size:11px;flex-shrink:0;}
.acct-card-title{font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:14px;color:var(--co-primary);flex:1;}
.acct-card-action{font-size:12px;font-weight:500;color:var(--co-primary);text-decoration:none;display:inline-flex;align-items:center;gap:5px;border:1px solid var(--co-hairline);border-radius:var(--r-sm);padding:5px 11px;transition:border-color .15s,background .15s;}
.acct-card-action:hover{border-color:var(--co-primary);background:var(--co-stone);color:var(--co-primary);}
.acct-card-body{padding:6px 18px;}

.acct-row{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;padding:11px 0;border-bottom:1px solid var(--co-hairline);}
.acct-row:last-child{border-bottom:none;}
.acct-row .lbl{font-family:'JetBrains Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:.8px;color:var(--co-muted);padding-top:2px;}
.acct-row .val{font-size:13px;color:var(--co-primary);text-align:right;}

.acct-stat-line{display:flex;flex-wrap:wrap;align-items:center;gap:14px;font-size:12px;color:var(--co-muted);margin-bottom:18px;}
.acct-stat-line .s-sep{width:1px;height:13px;background:var(--co-hairline);}
.acct-stat-line b{font-family:'Space Grotesk',sans-serif;font-weight:600;color:var(--co-primary);}

.acct-banner{display:flex;align-items:center;gap:11px;border-radius:12px;padding:12px 16px;margin-bottom:18px;background:var(--co-error-bg);border:1px solid var(--co-error-border);text-decoration:none;}
.acct-banner .ab-ico{width:30px;height:30px;border-radius:8px;background:#fff;color:var(--co-error);display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0;}
.acct-banner .ab-t{flex:1;min-width:0;}
.acct-banner .ab-title{font-size:13px;font-weight:600;color:var(--co-error);}
.acct-banner .ab-sub{font-size:12px;color:var(--co-body-muted);margin-top:1px;}
.acct-banner .ab-go{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--co-error);white-space:nowrap;}

.acct-textpill{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:600;letter-spacing:.3px;color:var(--co-muted);white-space:nowrap;}
.acct-textpill.is-warn{color:var(--co-amber-text);}
.acct-textpill.is-ok{color:var(--co-deep-green);}
.acct-textpill.is-danger{color:var(--co-error);}

.acct-amount{font-family:'Space Grotesk',sans-serif;font-size:1.05rem;font-weight:600;color:var(--co-primary);}
.acct-btn{font-size:12px;font-weight:500;color:var(--co-primary);background:#fff;border:1px solid var(--co-hairline);border-radius:var(--r-sm);padding:7px 13px;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:6px;white-space:nowrap;transition:border-color .15s,background .15s;}
.acct-btn:hover{border-color:var(--co-primary);background:var(--co-stone);color:var(--co-primary);}
.acct-btn.solid{background:var(--co-deep-green);border-color:var(--co-deep-green);color:#fff;}
.acct-btn.solid:hover{background:#16322c;border-color:#16322c;color:#fff;filter:none;}

.acct-empty{text-align:center;padding:64px 24px;border:1px dashed var(--co-hairline);border-radius:14px;color:var(--co-muted);background:var(--co-canvas);}
.acct-empty i{font-size:2.4rem;opacity:.22;display:block;margin-bottom:14px;}
.acct-empty h4{font-family:'Space Grotesk',sans-serif;font-weight:600;color:var(--co-primary);margin-bottom:6px;}
.acct-empty p{font-size:13px;margin-bottom:18px;}

/* ── Responsive: sidebar → top strip ──────────── */
@media(max-width:768px){
    .acct-layout{grid-template-columns:1fr;gap:16px;}
    .acct-side{position:static;}
    .acct-nav{flex-direction:row;overflow-x:auto;gap:4px;}
    .acct-nav-item{white-space:nowrap;}
    .acct-nav-sep{display:none;}
}
</style>

{% with cp=user.cafe_profile credit=user.credit_account %}
<aside class="acct-side">
    <div class="acct-profile">
        <div class="acct-id">
            <div class="acct-mono">{% if cp.cafe_name %}{{ cp.cafe_name|slice:":2"|upper }}{% else %}{{ user.username|slice:":2"|upper }}{% endif %}</div>
            <div style="min-width:0;">
                <div class="acct-name">{% if cp.cafe_name %}{{ cp.cafe_name }}{% else %}{{ user.username }}{% endif %}</div>
                <div class="acct-login">
                    {% if user.socialaccount_set.all %}<i class="fa-brands fa-google" style="font-size:10px;"></i>Google
                    {% elif user.email %}<i class="fa-solid fa-envelope" style="font-size:10px;"></i>Email
                    {% else %}<i class="fa-solid fa-mobile-screen" style="font-size:10px;"></i>OTP{% endif %}
                </div>
            </div>
        </div>
        {% if credit and credit.is_enabled %}
        <a href="/cafe/invoices/" class="acct-badge">
            <span>Tersedia Rp {{ credit.available_credit|floatformat:0 }}</span>
            <span class="ab-go"><i class="fa-solid fa-chevron-right"></i></span>
        </a>
        {% else %}
        <div class="acct-badge neutral"><span>Akun Kafe</span></div>
        {% endif %}
    </div>

    <nav class="acct-nav">
        <a href="/orders/" class="acct-nav-item {% if active == 'orders' %}active{% endif %}">
            <i class="fa-solid fa-receipt"></i> Pesanan Saya
        </a>
        {% if credit and credit.is_enabled %}
        <a href="/cafe/invoices/" class="acct-nav-item {% if active == 'invoices' %}active{% endif %}">
            <i class="fa-solid fa-file-invoice-dollar"></i> Tagihan Kredit
        </a>
        {% endif %}
        <a href="/accounts/profile/" class="acct-nav-item {% if active == 'profile' %}active{% endif %}">
            <i class="fa-solid fa-user"></i> Profil Kafe
        </a>
        <div class="acct-nav-sep"></div>
        <a href="/accounts/logout/" class="acct-nav-item danger">
            <i class="fa-solid fa-right-from-bracket"></i> Logout
        </a>
    </nav>
</aside>
{% endwith %}
```

Note: the monogram comes from `{{ cp.cafe_name|slice:":2"|upper }}` → "Kopi Kita" → "KO", which matches the `'>KO<'` assertion in Step 1.

- [ ] **Step 4: Run the test (passes after Task 4)**

Run: `python manage.py test apps.accounts.tests.AccountSidebarTests -v 2`
Expected: still FAIL until Task 4 includes the partial in `profile.html`. That is correct — the partial exists but is not yet wired. Proceed; this test is the acceptance gate for Task 4.

- [ ] **Step 5: Commit**

```bash
git add templates/partials/_account_sidebar.html apps/accounts/tests.py
git commit -m "feat(account): add shared account sidebar partial + shell CSS"
```

---

### Task 2: Redesign Pesanan Saya panel

Rewrite `order_history.html` to use the shell + sidebar and the warm-flat list style. No view changes (context already provides `orders`, `total_spent`, `pending_count`, `last_order`, `overdue_count`).

**Files:**
- Modify: `templates/cafe/order_history.html` (full replace of `page_css` + `content` blocks)

**Interfaces:**
- Consumes: shell classes from Task 1; context vars `orders`, `total_spent`, `pending_count`, `last_order`, `overdue_count` (unchanged from `apps/orders/views.py:order_list`).

- [ ] **Step 1: Replace the template**

Replace the entire contents of `templates/cafe/order_history.html` with:

```html
{% extends 'base_store.html' %}
{% block title %}Pesanan Saya — Sup Kopi{% endblock %}

{% block page_css %}
<style>
.po-list{display:flex;flex-direction:column;gap:8px;}
.po-card{border:1px solid var(--co-hairline);border-radius:12px;background:var(--co-canvas);box-shadow:0 1px 3px rgba(0,0,0,.05);border-left:3px solid var(--co-muted);padding:13px 16px;transition:border-color .15s;}
.po-card:hover{border-color:rgba(50,50,60,.22);}
.po-card.s-PENDING{border-left-color:var(--co-amber-dim);}
.po-card.s-CONFIRMED,.po-card.s-PROCESSING,.po-card.s-SHIPPED,.po-card.s-DELIVERED{border-left-color:var(--co-deep-green);}
.po-card.s-CANCELLED{border-left-color:var(--co-muted);}
.po-top{display:flex;align-items:center;justify-content:space-between;gap:12px;}
.po-num{font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:700;color:var(--co-primary);}
.po-meta{font-size:12px;color:var(--co-muted);}
.po-items{font-size:12px;color:var(--co-body-muted);margin:7px 0 10px;line-height:1.5;}
.po-bot{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;}
.po-actions{display:flex;align-items:center;gap:7px;flex-wrap:wrap;}
.po-reorder{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;border:1px solid var(--co-hairline);border-radius:12px;background:var(--co-stone);padding:11px 16px;margin-bottom:16px;}
.po-reorder .pr-eyebrow{font-family:'JetBrains Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:1.1px;color:var(--co-muted);}
.po-reorder .pr-items{font-size:12px;color:var(--co-body-muted);margin-top:2px;}
.po-reorder .pr-items b{color:var(--co-primary);font-weight:600;}
@media(max-width:560px){.po-bot{flex-direction:column;align-items:flex-start;}.po-actions{width:100%;}.po-actions .acct-btn{flex:1;justify-content:center;}}
</style>
{% endblock %}

{% block content %}
<div class="acct-layout">
{% include 'partials/_account_sidebar.html' with active='orders' %}
<div class="acct-main">

    <div class="acct-page-head">
        <div>
            <span class="acct-eyebrow">Kafe</span>
            <h1 class="acct-h1">Pesanan Saya</h1>
        </div>
        <a href="/produk/" class="acct-ghost-link"><i class="fa-solid fa-store" style="font-size:11px;"></i> Belanja Lagi</a>
    </div>

    {% if overdue_count %}
    <a href="/cafe/invoices/" class="acct-banner">
        <span class="ab-ico"><i class="fa-solid fa-triangle-exclamation"></i></span>
        <span class="ab-t">
            <span class="ab-title">{{ overdue_count }} tagihan kredit jatuh tempo</span>
            <span class="ab-sub">Segera lunasi agar fasilitas kredit tetap aktif.</span>
        </span>
        <span class="ab-go">Bayar <i class="fa-solid fa-arrow-right"></i></span>
    </a>
    {% endif %}

    {% if orders %}
    <div class="acct-stat-line">
        <span><b>{{ orders|length }}</b> order</span><span class="s-sep"></span>
        <span><b>Rp {{ total_spent|floatformat:0 }}</b> belanja</span><span class="s-sep"></span>
        <span><b>{{ pending_count }}</b> menunggu bayar</span>
    </div>

    {% if last_order %}
    <div class="po-reorder">
        <div>
            <div class="pr-eyebrow">Pesan lagi</div>
            <div class="pr-items"><b>{{ last_order.order_number }}</b> · {% for item in last_order.items.all|slice:":3" %}{{ item.product_name }}{% if not forloop.last %}, {% endif %}{% endfor %}{% if last_order.items.all|length > 3 %} +{{ last_order.items.all|length|add:"-3" }} lainnya{% endif %}</div>
        </div>
        <form method="post" action="/orders/{{ last_order.order_number }}/reorder/" style="margin:0;">{% csrf_token %}
            <button type="submit" class="acct-btn solid"><i class="fa-solid fa-rotate-right" style="font-size:10px;"></i> Ulangi Pesanan</button>
        </form>
    </div>
    {% endif %}

    <div class="po-list">
    {% for order in orders %}
        <div class="po-card s-{{ order.status }}">
            <div class="po-top">
                <div><span class="po-num">{{ order.order_number }}</span> <span class="po-meta">· {{ order.created_at|date:"d M Y" }} · {{ order.items.all|length }} produk</span></div>
                <span class="acct-textpill {% if order.status == 'PENDING' %}is-warn{% elif order.status == 'CANCELLED' %}is-danger{% else %}is-ok{% endif %}">{{ order.get_status_display }}</span>
            </div>
            <div class="po-items">
                {% with total=order.items.all|length %}{% for item in order.items.all|slice:":3" %}{{ item.product_name }} ×{{ item.quantity }}{% if not forloop.last %} · {% endif %}{% endfor %}{% if total > 3 %} · +{{ total|add:"-3" }} lainnya{% endif %}{% endwith %}
            </div>
            <div class="po-bot">
                <span class="acct-amount">Rp {{ order.total_amount|floatformat:0 }}</span>
                <div class="po-actions">
                    {% if order.status == 'PENDING' %}<a href="/payments/pay/{{ order.order_number }}/" class="acct-btn solid"><i class="fa-solid fa-lock" style="font-size:10px;"></i> Bayar</a>{% endif %}
                    <form method="post" action="/orders/{{ order.order_number }}/reorder/" style="margin:0;">{% csrf_token %}<button type="submit" class="acct-btn"><i class="fa-solid fa-rotate-right" style="font-size:10px;"></i> Pesan Lagi</button></form>
                    <a href="/orders/{{ order.order_number }}/" class="acct-btn">Detail <i class="fa-solid fa-arrow-right" style="font-size:9px;"></i></a>
                </div>
            </div>
        </div>
    {% endfor %}
    </div>

    {% else %}
    <div class="acct-empty">
        <i class="fa-solid fa-receipt"></i>
        <h4>Belum ada order</h4>
        <p>Mulai pilih produk kopi untuk kafe kamu.</p>
        <a href="/produk/" class="acct-btn solid"><i class="fa-solid fa-store"></i> Lihat Produk</a>
    </div>
    {% endif %}

</div>
</div>
{% endblock %}
```

- [ ] **Step 2: Verify it renders**

Run: `python manage.py test apps.orders -v 1`
Expected: PASS (no orders-app tests should break; this confirms the template has no syntax errors via any view test). If `apps.orders` has no tests, instead run `python manage.py check` — Expected: "System check identified no issues".

- [ ] **Step 3: Visual check**

Run the dev server, log in as a cafe user, open `/orders/`. Confirm: sidebar present with "Pesanan Saya" active (green), stat line renders, order cards flat with left status accent, no heavy shadows, reorder strip is the quiet stone variant.

- [ ] **Step 4: Commit**

```bash
git add templates/cafe/order_history.html
git commit -m "feat(account): redesign Pesanan Saya into account shell"
```

---

### Task 3: Redesign Tagihan Kredit panel

Rewrite `invoices.html` to use shell + sidebar, flatten the credit summary, and remove coral/`translateY`/heavy shadows.

**Files:**
- Modify: `templates/cafe/invoices.html` (full replace)

**Interfaces:**
- Consumes: shell classes from Task 1; context vars `credit`, `utilization`, `invoices` (unchanged from the existing invoices view).

- [ ] **Step 1: Replace the template**

Replace the entire contents of `templates/cafe/invoices.html` with:

```html
{% extends 'base_store.html' %}
{% block title %}Tagihan Kredit — Sup Kopi{% endblock %}

{% block page_css %}
<style>
.ti-summary{border:1px solid var(--co-hairline);border-radius:14px;background:var(--co-canvas);box-shadow:0 1px 3px rgba(0,0,0,.05);padding:20px 22px;margin-bottom:20px;}
.ti-avail .lbl{font-family:'JetBrains Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--co-muted);}
.ti-avail .val{font-family:'Space Grotesk',sans-serif;font-size:2rem;font-weight:600;letter-spacing:-.02em;color:var(--co-deep-green);line-height:1.1;margin-top:2px;}
.ti-substats{display:flex;gap:22px;flex-wrap:wrap;margin:14px 0 16px;}
.ti-substats .lbl{font-family:'JetBrains Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:.8px;color:var(--co-muted);}
.ti-substats .v{font-family:'Space Grotesk',sans-serif;font-size:1.05rem;font-weight:600;color:var(--co-primary);margin-top:2px;}
.ti-substats .v.danger{color:var(--co-error);}
.ti-util-head{display:flex;justify-content:space-between;align-items:baseline;font-size:12px;margin-bottom:7px;}
.ti-util-head .lbl{color:var(--co-muted);}
.ti-util-head .pct{font-family:'Space Grotesk',sans-serif;font-weight:600;color:var(--co-primary);}
.ti-track{height:6px;border-radius:var(--r-xl);background:var(--co-stone);overflow:hidden;}
.ti-fill{height:100%;border-radius:var(--r-xl);background:var(--co-deep-green);transition:width .4s cubic-bezier(.2,.8,.2,1);}
.ti-fill.warn{background:var(--co-amber-dim);}
.ti-fill.danger{background:var(--co-error);}
.ti-note{font-size:11px;color:var(--co-muted);margin-top:8px;}
.ti-sectitle{font-family:'JetBrains Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:1.4px;color:var(--co-muted);margin-bottom:12px;}
.ti-list{display:flex;flex-direction:column;gap:8px;}
.ti-card{border:1px solid var(--co-hairline);border-radius:12px;background:var(--co-canvas);box-shadow:0 1px 3px rgba(0,0,0,.05);padding:14px 16px;display:grid;grid-template-columns:1fr auto;gap:8px 18px;align-items:center;transition:border-color .15s;}
.ti-card:hover{border-color:rgba(50,50,60,.22);}
.ti-card.is-overdue{border-color:var(--co-error-border);background:var(--co-error-bg);}
.ti-num{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--co-muted);margin-bottom:3px;}
.ti-due{font-size:12px;color:var(--co-muted);margin-top:5px;}
.ti-due .urgent{color:var(--co-error);font-weight:600;}
.ti-due .soon{color:var(--co-amber-text);font-weight:600;}
.ti-reject{font-size:12px;color:var(--co-error);margin-top:8px;background:#fff;border:1px solid var(--co-error-border);border-radius:var(--r-sm);padding:7px 11px;}
.ti-side{display:flex;flex-direction:column;align-items:flex-end;gap:9px;}
.ti-actions{display:flex;align-items:center;gap:12px;flex-wrap:wrap;justify-content:flex-end;}
.ti-link{font-size:12px;color:var(--co-muted);text-decoration:none;white-space:nowrap;transition:color .15s;display:inline-flex;align-items:center;gap:5px;}
.ti-link:hover{color:var(--co-primary);}
@media(max-width:560px){.ti-card{grid-template-columns:1fr;}.ti-side{align-items:stretch;}.ti-actions{justify-content:flex-start;}}
</style>
{% endblock %}

{% block content %}
<div class="acct-layout">
{% include 'partials/_account_sidebar.html' with active='invoices' %}
<div class="acct-main">

    <div class="acct-page-head">
        <div>
            <span class="acct-eyebrow">Kredit Dagang</span>
            <h1 class="acct-h1">Tagihan Kredit</h1>
        </div>
        <a href="/orders/" class="acct-ghost-link"><i class="fa-solid fa-arrow-left" style="font-size:11px;"></i> Pesanan Saya</a>
    </div>

    <div class="ti-summary">
        <div class="ti-avail">
            <div class="lbl">Kredit Tersedia</div>
            <div class="val">Rp {{ credit.available_credit|floatformat:0 }}</div>
        </div>
        <div class="ti-substats">
            <div><div class="lbl">Limit Kredit</div><div class="v">Rp {{ credit.credit_limit|floatformat:0 }}</div></div>
            <div><div class="lbl">Outstanding</div><div class="v {% if credit.outstanding_balance > 0 %}danger{% endif %}">Rp {{ credit.outstanding_balance|floatformat:0 }}</div></div>
        </div>
        <div class="ti-util-head"><span class="lbl">Penggunaan kredit</span><span class="pct">{{ utilization }}%</span></div>
        <div class="ti-track"><div class="ti-fill {% if utilization >= 90 %}danger{% elif utilization >= 70 %}warn{% endif %}" style="width:{% if utilization > 100 %}100{% else %}{{ utilization }}{% endif %}%;"></div></div>
        <div class="ti-note">Jangka waktu pelunasan {{ credit.payment_term_days }} hari · {% if credit.is_enabled %}Fasilitas kredit aktif{% else %}Fasilitas kredit nonaktif{% endif %}</div>
    </div>

    <div class="ti-sectitle">Riwayat Tagihan</div>
    <div class="ti-list">
        {% for inv in invoices %}
        <div class="ti-card {% if inv.is_overdue %}is-overdue{% endif %}">
            <div>
                <div class="ti-num">{{ inv.order.order_number }}</div>
                <div class="acct-amount">Rp {{ inv.amount|floatformat:0 }}</div>
                <div class="ti-due">
                    Jatuh tempo {{ inv.due_date|date:'d M Y' }}
                    {% if inv.status == 'UNPAID' or inv.status == 'OVERDUE' %}{% if inv.days_left < 0 %}<span class="urgent">· Telat {{ inv.days_left|stringformat:'d'|cut:'-' }} hari</span>{% elif inv.days_left == 0 %}<span class="urgent">· Hari ini</span>{% elif inv.days_left <= 7 %}<span class="soon">· {{ inv.days_left }} hari lagi</span>{% else %}<span>· {{ inv.days_left }} hari lagi</span>{% endif %}{% endif %}
                </div>
                {% if inv.rejection_reason %}<div class="ti-reject"><i class="fa-solid fa-circle-xmark me-1"></i>Bukti ditolak: {{ inv.rejection_reason }}</div>{% endif %}
            </div>
            <div class="ti-side">
                {% if inv.status == 'PAID' %}<span class="acct-textpill is-ok">Lunas</span>
                {% elif inv.status == 'VERIFYING' %}<span class="acct-textpill is-warn">Menunggu Verifikasi</span>
                {% elif inv.status == 'OVERDUE' or inv.is_overdue %}<span class="acct-textpill is-danger">Jatuh Tempo</span>
                {% else %}<span class="acct-textpill">Belum Dibayar</span>{% endif %}
                <div class="ti-actions">
                    {% if inv.status == 'UNPAID' or inv.status == 'OVERDUE' %}
                        <a href="/payments/invoice/{{ inv.id }}/pay-online/" class="acct-btn solid"><i class="fa-solid fa-credit-card" style="font-size:11px;"></i> Bayar Online</a>
                        <a href="/cafe/invoices/{{ inv.id }}/upload/" class="ti-link"><i class="fa-solid fa-upload"></i> Transfer manual</a>
                        <a href="/cafe/invoices/{{ inv.id }}/pdf/" class="ti-link" target="_blank"><i class="fa-solid fa-file-pdf"></i> PDF</a>
                    {% elif inv.status == 'VERIFYING' %}
                        <span class="ti-link" style="cursor:default;"><i class="fa-solid fa-hourglass-half"></i> Menunggu konfirmasi</span>
                        <a href="/cafe/invoices/{{ inv.id }}/pdf/" class="ti-link" target="_blank"><i class="fa-solid fa-file-pdf"></i> PDF</a>
                    {% elif inv.status == 'PAID' %}
                        <a href="/cafe/invoices/{{ inv.id }}/pdf/" class="ti-link" target="_blank"><i class="fa-solid fa-file-pdf"></i> Download Invoice</a>
                    {% endif %}
                </div>
            </div>
        </div>
        {% empty %}
        <div class="acct-empty"><i class="fa-solid fa-file-invoice"></i><p style="margin:0;">Belum ada tagihan kredit.</p></div>
        {% endfor %}
    </div>

</div>
</div>
{% endblock %}
```

- [ ] **Step 2: Verify**

Run: `python manage.py check`
Expected: "System check identified no issues". Then run any invoices/payments view test if present: `python manage.py test apps.payments -v 1` — Expected: PASS.

- [ ] **Step 3: Visual check**

Log in as a cafe user with credit enabled, open `/cafe/invoices/`. Confirm sidebar "Tagihan Kredit" active, large green "Tersedia" figure, thin flat utilization bar, invoice cards flat, "Bayar Online" is green flat (no coral, no lift).

- [ ] **Step 4: Commit**

```bash
git add templates/cafe/invoices.html
git commit -m "feat(account): redesign Tagihan Kredit into account shell"
```

---

### Task 4: Redesign Profil Kafe (read view) + Edit affordance

Rewrite `profile.html` to use shell + grouped list cards, with an "Edit" action linking to the new edit route (built in Task 5). This task completes the Task 1 acceptance test.

**Files:**
- Modify: `templates/accounts/profile.html` (full replace)

**Interfaces:**
- Consumes: shell classes from Task 1; context `user`, `profile` (from `profile_view`). Links to `/accounts/profile/edit/` (route created in Task 5).

- [ ] **Step 1: Replace the template**

Replace the entire contents of `templates/accounts/profile.html` with:

```html
{% extends 'base_store.html' %}
{% block title %}Profil Kafe — Sup Kopi{% endblock %}

{% block content %}
<div class="acct-layout">
{% include 'partials/_account_sidebar.html' with active='profile' %}
<div class="acct-main">

    <div class="acct-page-head">
        <div>
            <span class="acct-eyebrow">Akun</span>
            <h1 class="acct-h1">Profil Kafe</h1>
        </div>
    </div>

    <div class="acct-card">
        <div class="acct-card-head">
            <div class="acct-card-ico"><i class="fa-solid fa-user"></i></div>
            <div class="acct-card-title">Informasi Akun</div>
        </div>
        <div class="acct-card-body">
            <div class="acct-row"><span class="lbl">Username</span><span class="val">{{ user.username }}</span></div>
            <div class="acct-row"><span class="lbl">Email</span><span class="val">{{ user.email|default:"—" }}</span></div>
            <div class="acct-row"><span class="lbl">No. HP</span><span class="val">{{ user.phone|default:"—" }}</span></div>
            <div class="acct-row"><span class="lbl">Role</span><span class="val">{{ user.get_role_display }}</span></div>
        </div>
    </div>

    {% if profile %}
    <div class="acct-card">
        <div class="acct-card-head">
            <div class="acct-card-ico"><i class="fa-solid fa-store"></i></div>
            <div class="acct-card-title">Informasi Kafe</div>
            <a href="/accounts/profile/edit/" class="acct-card-action"><i class="fa-solid fa-pen" style="font-size:10px;"></i> Edit</a>
        </div>
        <div class="acct-card-body">
            <div class="acct-row"><span class="lbl">Nama Kafe</span><span class="val"><strong>{{ profile.cafe_name }}</strong></span></div>
            <div class="acct-row"><span class="lbl">Alamat</span><span class="val">{{ profile.address|default:"—" }}</span></div>
            <div class="acct-row"><span class="lbl">Kota</span><span class="val">{{ profile.city|default:"—" }}</span></div>
            <div class="acct-row"><span class="lbl">Provinsi</span><span class="val">{{ profile.province|default:"—" }}</span></div>
            <div class="acct-row"><span class="lbl">Kode Pos</span><span class="val">{{ profile.postal_code|default:"—" }}</span></div>
        </div>
    </div>
    {% endif %}

</div>
</div>
{% endblock %}
```

- [ ] **Step 2: Run the Task 1 acceptance test**

Run: `python manage.py test apps.accounts.tests.AccountSidebarTests -v 2`
Expected: PASS (sidebar now wired; `'>KO<'`, nav links, and `acct-nav-item active` all present).

- [ ] **Step 3: Commit**

```bash
git add templates/accounts/profile.html
git commit -m "feat(account): redesign Profil Kafe with grouped list cards"
```

---

### Task 5: Editable profile — form, view, url, template

Adds `/accounts/profile/edit/` so cafe owners can edit cafe fields and phone. `username`, `email`, `role` are not editable.

**Files:**
- Modify: `apps/accounts/forms.py` (add `ProfileEditForm`)
- Modify: `apps/accounts/views.py` (add `profile_edit`)
- Modify: `apps/accounts/urls.py` (add route)
- Create: `templates/accounts/profile_edit.html`
- Modify: `apps/accounts/tests.py` (add `ProfileEditTests`)

**Interfaces:**
- Produces: `ProfileEditForm(forms.ModelForm)` over `CafeProfile` with extra `phone` field; `.save(user)` persists CafeProfile fields and writes `phone` onto the passed `user`. View name `profile_edit` at `/accounts/profile/edit/`.

- [ ] **Step 1: Write the failing test**

Add to `apps/accounts/tests.py`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `python manage.py test apps.accounts.tests.ProfileEditTests -v 2`
Expected: FAIL — `NoReverseMatch: 'profile_edit'`.

- [ ] **Step 3: Add the form**

Append to `apps/accounts/forms.py`:

```python
class ProfileEditForm(forms.ModelForm):
    phone = forms.CharField(max_length=20, required=False)

    class Meta:
        model = CafeProfile
        fields = ['cafe_name', 'address', 'city', 'province', 'postal_code']
        widgets = {'address': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['phone'].initial = self.instance.user.phone

    def save(self, commit=True):
        profile = super().save(commit=commit)
        if commit:
            profile.user.phone = self.cleaned_data.get('phone', '')
            profile.user.save(update_fields=['phone'])
        return profile
```

- [ ] **Step 4: Add the view**

In `apps/accounts/views.py`, add (near `profile_view`); ensure `ProfileEditForm` is imported from `.forms` and `messages` is imported:

```python
@login_required
def profile_edit(request):
    if not request.user.is_cafe:
        return redirect('profile')
    profile = get_object_or_404(CafeProfile, user=request.user)
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil kafe berhasil diperbarui.')
            return redirect('profile')
    else:
        form = ProfileEditForm(instance=profile)
    return render(request, 'accounts/profile_edit.html', {'form': form})
```

If `get_object_or_404`, `messages`, or `ProfileEditForm` are not already imported at the top of `views.py`, add:
```python
from django.shortcuts import get_object_or_404
from django.contrib import messages
from .forms import ProfileEditForm  # merge into existing forms import if present
```

- [ ] **Step 5: Add the route**

In `apps/accounts/urls.py`, add below the `profile/` line:

```python
    path('profile/edit/', views.profile_edit, name='profile_edit'),
```

- [ ] **Step 6: Create the edit template**

Create `templates/accounts/profile_edit.html`:

```html
{% extends 'base_store.html' %}
{% block title %}Edit Profil Kafe — Sup Kopi{% endblock %}

{% block page_css %}
<style>
.pe-form{max-width:520px;}
.pe-field{margin-bottom:14px;}
.pe-field label{display:block;font-family:'JetBrains Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:.8px;color:var(--co-muted);margin-bottom:5px;}
.pe-field input,.pe-field textarea{width:100%;font-size:13px;padding:7px 11px;border:1px solid var(--co-hairline);border-radius:var(--r-sm);background:var(--co-canvas);color:var(--co-primary);font-family:inherit;}
.pe-field input:focus,.pe-field textarea:focus{outline:none;border-color:var(--co-deep-green);}
.pe-actions{display:flex;gap:8px;margin-top:18px;}
.pe-err{font-size:11px;color:var(--co-error);margin-top:4px;}
</style>
{% endblock %}

{% block content %}
<div class="acct-layout">
{% include 'partials/_account_sidebar.html' with active='profile' %}
<div class="acct-main">

    <div class="acct-page-head">
        <div>
            <span class="acct-eyebrow">Akun</span>
            <h1 class="acct-h1">Edit Profil Kafe</h1>
        </div>
        <a href="/accounts/profile/" class="acct-ghost-link"><i class="fa-solid fa-arrow-left" style="font-size:11px;"></i> Kembali</a>
    </div>

    <div class="acct-card">
        <div class="acct-card-head">
            <div class="acct-card-ico"><i class="fa-solid fa-store"></i></div>
            <div class="acct-card-title">Informasi Kafe</div>
        </div>
        <div class="acct-card-body" style="padding:16px 18px;">
            <form method="post" class="pe-form">{% csrf_token %}
                {% for field in form %}
                <div class="pe-field">
                    <label for="{{ field.id_for_label }}">{{ field.label }}</label>
                    {{ field }}
                    {% for err in field.errors %}<div class="pe-err">{{ err }}</div>{% endfor %}
                </div>
                {% endfor %}
                <div class="pe-actions">
                    <button type="submit" class="acct-btn solid"><i class="fa-solid fa-check" style="font-size:11px;"></i> Simpan</button>
                    <a href="/accounts/profile/" class="acct-btn">Batal</a>
                </div>
            </form>
        </div>
    </div>

</div>
</div>
{% endblock %}
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python manage.py test apps.accounts.tests.ProfileEditTests -v 2`
Expected: PASS (all three tests).

- [ ] **Step 8: Run the full accounts suite**

Run: `python manage.py test apps.accounts -v 1`
Expected: PASS (AccountSidebarTests + ProfileEditTests).

- [ ] **Step 9: Commit**

```bash
git add apps/accounts/forms.py apps/accounts/views.py apps/accounts/urls.py templates/accounts/profile_edit.html apps/accounts/tests.py
git commit -m "feat(account): editable cafe profile (form, view, route, template)"
```

---

## Self-Review Notes

- **Spec coverage:** shell+sidebar (Task 1), warm-flat cards & tokens (all tasks), Pesanan redesign (Task 2), Tagihan flatten + remove coral/translateY (Task 3), Profil grouped list + edit affordance (Task 4), editable profile route/form/template with read-only username/email/role (Task 5), responsive sidebar→strip (Task 1 CSS), badge = available credit (Task 1). All spec sections mapped.
- **Monogram note:** spec said "inisial"; implementation uses first two letters of cafe name (e.g. "KO" for "Kopi Kita"). Task 1 Step 3 flags that the Step 1 test assertion must read `'>KO<'` to match. Keep them consistent.
- **No new colors:** badge gradient uses the existing deep-green literals (`#1b3b34`/`#2e5b4f`) already present in the codebase's deep-green family; everything else uses `var(--co-*)` tokens.
- **Login method:** derived in-template from `user.socialaccount_set.all` (allauth reverse relation) — no view change.
```
