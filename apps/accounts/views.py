from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.core import signing
from django.conf import settings as django_settings
from .forms import CafeRegistrationForm
from .models import CafeProfile, EmailOTP, StaffInvitation, SupplierStaff, User

BACKEND = 'django.contrib.auth.backends.ModelBackend'
TRUSTED_DEVICE_COOKIE = 'sup_trusted'
TRUSTED_DEVICE_DAYS = 7


def _send_otp_email(user, otp, subject='Kode OTP Login Sup Kopi'):
    html = render_to_string('email/otp.html', {'code': otp.code})
    plain = f'Kode OTP kamu: {otp.code}\n\nBerlaku 10 menit. Jangan bagikan ke siapapun.'
    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain,
        from_email=django_settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html, 'text/html')
    msg.send()


def _set_trusted_cookie(response, user):
    value = signing.dumps({'uid': user.pk}, salt='trusted-device')
    response.set_cookie(
        TRUSTED_DEVICE_COOKIE,
        value,
        max_age=TRUSTED_DEVICE_DAYS * 86400,
        httponly=True,
        samesite='Lax',
    )


def _is_trusted_device(request, user):
    raw = request.COOKIES.get(TRUSTED_DEVICE_COOKIE)
    if not raw:
        return False
    try:
        data = signing.loads(raw, salt='trusted-device',
                             max_age=TRUSTED_DEVICE_DAYS * 86400)
        return data.get('uid') == user.pk
    except Exception:
        return False


def register_cafe(request):
    if request.user.is_authenticated:
        return redirect('/')
    if request.method == 'POST':
        form = CafeRegistrationForm(request.POST)
        if form.is_valid():
            # Remove any stale inactive registrations for this email
            User.objects.filter(email=form.cleaned_data['email'], is_active=False).delete()
            user = form.save()
            user.is_active = False
            user.save(update_fields=['is_active'])
            otp = EmailOTP.generate(user)
            _send_otp_email(user, otp, subject='Kode OTP Verifikasi Pendaftaran Sup Kopi')
            request.session['register_user_id'] = user.pk
            return redirect('/accounts/register/verify/')
    else:
        form = CafeRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


def register_otp_verify(request):
    user_id = request.session.get('register_user_id')
    if not user_id:
        return redirect('/accounts/register/')

    user = get_object_or_404(User, pk=user_id, is_active=False)

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        otp = (
            EmailOTP.objects
            .filter(user=user, is_used=False)
            .order_by('-created_at')
            .first()
        )

        if not otp or otp.is_expired:
            messages.error(request, 'Kode OTP sudah kedaluwarsa. Minta kode baru.')
            return render(request, 'accounts/register_otp.html', {'email': user.email})

        if otp.code != code:
            messages.error(request, 'Kode OTP salah.')
            return render(request, 'accounts/register_otp.html', {'email': user.email})

        otp.is_used = True
        otp.save()
        user.is_active = True
        user.save(update_fields=['is_active'])
        del request.session['register_user_id']
        login(request, user, backend=BACKEND)
        messages.success(request, 'Akun berhasil dibuat dan diverifikasi!')
        return redirect('/')

    return render(request, 'accounts/register_otp.html', {'email': user.email})


def register_otp_resend(request):
    user_id = request.session.get('register_user_id')
    if not user_id:
        return redirect('/accounts/register/')

    user = get_object_or_404(User, pk=user_id, is_active=False)
    otp = EmailOTP.generate(user)
    _send_otp_email(user, otp, subject='Kode OTP Verifikasi Pendaftaran Sup Kopi (Baru)')
    messages.success(request, 'Kode OTP baru sudah dikirim ke email kamu.')
    return redirect('/accounts/register/verify/')


@login_required
def google_setup(request):
    """Complete cafe profile after Google signup."""
    try:
        profile = request.user.cafe_profile
    except CafeProfile.DoesNotExist:
        profile = CafeProfile(user=request.user)

    if request.method == 'POST':
        cafe_name = request.POST.get('cafe_name', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        province = request.POST.get('province', '').strip()
        postal_code = request.POST.get('postal_code', '').strip()

        errors = []
        if not cafe_name:
            errors.append('Nama kafe tidak boleh kosong.')
        if not city:
            errors.append('Kota tidak boleh kosong.')
        if not province:
            errors.append('Provinsi tidak boleh kosong.')
        if not postal_code:
            errors.append('Kode pos tidak boleh kosong.')

        if not errors:
            profile.cafe_name = cafe_name
            profile.address = address
            profile.city = city
            profile.province = province
            profile.postal_code = postal_code
            profile.save()
            messages.success(request, 'Profil kafe berhasil disimpan. Selamat bergabung!')
            return redirect('/')

        return render(request, 'accounts/google_setup.html', {
            'profile': profile,
            'errors': errors,
            'post': request.POST,
        })

    return render(request, 'accounts/google_setup.html', {'profile': profile})


def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_any_supplier:
            return redirect('/supplier/dashboard/')
        return redirect('/')

    next_url = request.GET.get('next', '/')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        next_url = request.POST.get('next', '/')
        try:
            found = User.objects.get(email__iexact=email, is_active=True)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            found = None

        user = authenticate(request, username=found.username, password=password) if found else None

        if user:
            if user.is_any_supplier:
                return redirect('/accounts/supplier/login/')
            login(request, user, backend=BACKEND)
            messages.success(request, f'Selamat datang, {user.username}!')
            return redirect(next_url if next_url.startswith('/') else '/')

        if found and not found.has_usable_password() and found.socialaccount_set.filter(provider='google').exists():
            messages.error(request, 'Akun ini terdaftar via Google dan belum punya password. Gunakan "Lupa password?" untuk set password, atau klik Login Google.')
        else:
            messages.error(request, 'Email atau password salah.')

    return render(request, 'accounts/login.html', {'next': next_url})


def logout_view(request):
    logout(request)
    messages.success(request, 'Kamu berhasil logout. Sampai jumpa!')
    response = redirect('/accounts/login/')
    response.delete_cookie(TRUSTED_DEVICE_COOKIE)
    return response


@login_required
def profile_view(request):
    profile = None
    if request.user.is_cafe:
        try:
            profile = request.user.cafe_profile
        except CafeProfile.DoesNotExist:
            pass
    return render(request, 'accounts/profile.html', {'profile': profile})


def supplier_login(request):
    if request.user.is_authenticated and request.user.is_any_supplier:
        return redirect('/supplier/dashboard/')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user and user.is_any_supplier:
            if _is_trusted_device(request, user):
                login(request, user, backend=BACKEND)
                messages.success(request, f'Selamat datang kembali, {user.username}!')
                return redirect('/supplier/dashboard/')

            if not user.email:
                messages.error(request, 'Akun ini belum memiliki email. Hubungi administrator.')
                return render(request, 'accounts/supplier_login.html')

            otp = EmailOTP.generate(user)
            _send_otp_email(user, otp)
            request.session['otp_user_id'] = user.pk
            return redirect('/accounts/supplier/verify/')

        messages.error(request, 'Username atau password salah.')

    return render(request, 'accounts/supplier_login.html')


def supplier_otp_verify(request):
    user_id = request.session.get('otp_user_id')
    if not user_id:
        return redirect('/accounts/supplier/login/')

    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        otp = (
            EmailOTP.objects
            .filter(user=user, is_used=False)
            .order_by('-created_at')
            .first()
        )

        if not otp or otp.is_expired:
            messages.error(request, 'Kode OTP sudah kedaluwarsa. Minta kode baru.')
            return render(request, 'accounts/supplier_otp.html', {'email': user.email})

        if otp.code != code:
            messages.error(request, 'Kode OTP salah.')
            return render(request, 'accounts/supplier_otp.html', {'email': user.email})

        otp.is_used = True
        otp.save()
        del request.session['otp_user_id']
        login(request, user, backend=BACKEND)
        messages.success(request, f'Selamat datang, {user.username}!')
        response = redirect('/supplier/dashboard/')
        _set_trusted_cookie(response, user)
        return response

    return render(request, 'accounts/supplier_otp.html', {'email': user.email})


def supplier_otp_resend(request):
    user_id = request.session.get('otp_user_id')
    if not user_id:
        return redirect('/accounts/supplier/login/')

    user = get_object_or_404(User, pk=user_id)
    otp = EmailOTP.generate(user)
    _send_otp_email(user, otp, subject='Kode OTP Login Sup Kopi (Baru)')
    messages.success(request, 'Kode OTP baru sudah dikirim ke email kamu.')
    return redirect('/accounts/supplier/verify/')


def staff_setup(request, token):
    invitation = get_object_or_404(StaffInvitation, token=token)

    if invitation.is_used:
        return render(request, 'accounts/staff_setup_invalid.html', {'reason': 'used'})
    if invitation.is_expired:
        return render(request, 'accounts/staff_setup_invalid.html', {'reason': 'expired'})

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        errors = []
        if not username:
            errors.append('Username tidak boleh kosong.')
        elif User.objects.filter(username=username).exists():
            errors.append(f'Username "{username}" sudah digunakan.')
        if len(password) < 8:
            errors.append('Password minimal 8 karakter.')
        if password != password2:
            errors.append('Konfirmasi password tidak cocok.')

        if errors:
            return render(request, 'accounts/staff_setup.html', {
                'invitation': invitation,
                'errors': errors,
                'username': username,
            })

        user = User.objects.create_user(
            username=username,
            email=invitation.email,
            password=password,
            role='supplier_staff',
        )
        SupplierStaff.objects.create(
            user=user,
            role=invitation.role,
            created_by=invitation.invited_by,
        )
        invitation.is_used = True
        invitation.save()

        login(request, user, backend=BACKEND)
        messages.success(request, f'Selamat datang, {username}! Akun kamu sudah aktif.')
        return redirect('/supplier/deliveries/' if user.staff_profile.is_logistics
                        else '/supplier/orders/')

    return render(request, 'accounts/staff_setup.html', {'invitation': invitation})
