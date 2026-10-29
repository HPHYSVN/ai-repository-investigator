from cart import cart_total
from pricing import format_price


def checkout_total(items):
    return format_price(cart_total(items))
