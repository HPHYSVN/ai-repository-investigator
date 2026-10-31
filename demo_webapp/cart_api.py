from cart import cart_total
from pricing import format_price

def checkout(items):
    """POST /api/checkout handler: returns the rendered cart total."""
    return {"total": format_price(cart_total(items))}
