from django import template

register = template.Library()

@register.filter
def currency(value, symbol="₵"):
    """
    Formats a number with commas, 2 decimals, and currency symbol.
    Example: 12345.5 -> ₵12,345.50
    """
    try:
        return f"{symbol}{float(value):,.2f}"
    except (ValueError, TypeError):
        return value
