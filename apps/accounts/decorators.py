from functools import wraps
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def supplier_required(view_func):
    """Owner supplier atau staff mana saja."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        if not request.user.is_any_supplier:
            raise PermissionDenied
        if request.user.is_supplier_staff and not request.user.staff_profile.is_active:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


def supplier_admin_required(view_func):
    """Owner supplier atau staff dengan role ADMIN."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        if request.user.is_supplier:
            return view_func(request, *args, **kwargs)
        if request.user.is_supplier_staff:
            profile = request.user.staff_profile
            if profile.is_active and profile.is_admin:
                return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return wrapper


def supplier_owner_required(view_func):
    """Hanya owner supplier (bukan staff)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        if not request.user.is_supplier:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


def cafe_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        if not request.user.is_cafe:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper
