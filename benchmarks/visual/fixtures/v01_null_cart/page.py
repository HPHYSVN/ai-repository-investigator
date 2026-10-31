from cart import cart_total

def render_total(prices):
    return f"Total: {cart_total(prices):.2f}"
