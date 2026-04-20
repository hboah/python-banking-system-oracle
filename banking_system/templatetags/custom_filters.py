from django import template

register = template.Library()

@register.filter
def prettify(value):
    return value.replace("_", " ").title()