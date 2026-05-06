from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from .models import CafeProfile


class CafeAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        if request.user.is_any_supplier:
            return '/supplier/dashboard/'
        return '/'


class CafeSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """Link existing user by email if they already have an account."""
        if sociallogin.is_existing:
            return
        email = sociallogin.account.extra_data.get('email', '')
        if not email:
            return
        from .models import User
        try:
            existing = User.objects.get(email=email)
            sociallogin.connect(request, existing)
        except User.DoesNotExist:
            pass

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        if not user.role or user.role == 'cafe':
            user.role = 'cafe'
            user.save(update_fields=['role'])

        if not hasattr(user, 'cafe_profile'):
            extra = sociallogin.account.extra_data
            name = extra.get('name', '') or user.username
            CafeProfile.objects.get_or_create(
                user=user,
                defaults={
                    'cafe_name': name,
                    'city': '',
                    'province': '',
                    'postal_code': '',
                }
            )
        return user
