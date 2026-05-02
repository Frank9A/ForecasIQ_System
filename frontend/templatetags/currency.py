from django import template

register = template.Library()

@register.filter
def naira(value):
    try:
        # Formats the number with commas and 2 decimal places
        return f"₦{float(value):,.2f}"
    except (ValueError, TypeError):
        return value