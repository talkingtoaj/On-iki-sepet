from django import template

from onikisepet.money_input import format_display_decimal

register = template.Library()


@register.filter(name="money")
def money(value):
    return format_display_decimal(value)
