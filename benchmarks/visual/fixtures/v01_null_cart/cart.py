def cart_total(prices):
    total = 0.0
    for p in prices:
        if p is None:
            return None
        total += p
    return total
