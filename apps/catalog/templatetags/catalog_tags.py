from django import template

register = template.Library()


@register.filter
def rupiah(value):
    """Format angka ke format Rupiah Indonesia: 50000 → 50.000"""
    try:
        value = int(float(value))
        return f"{value:,}".replace(",", ".")
    except (ValueError, TypeError):
        return value


@register.filter
def rupiah_short(value):
    """Format singkat: 1500000 → 1,5 jt | 500000 → 500 rb"""
    try:
        value = int(float(value))
        if value >= 1_000_000:
            n = value / 1_000_000
            return f"{n:g} jt"
        if value >= 1_000:
            n = value / 1_000
            return f"{n:g} rb"
        return str(value)
    except (ValueError, TypeError):
        return value
