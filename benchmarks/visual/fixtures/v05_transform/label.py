from money import cents_to_dollars

def price_label(cents):
    return f"${cents_to_dollars(cents):.2f}"
