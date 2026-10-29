from catalog import get_product


def cart_total(items):
    total = 0.0
    for sku, qty in items:
        product = get_product(sku)
        if product is None:
            return None
        total += product["price"] * qty
    return total
