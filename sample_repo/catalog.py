PRODUCTS = {
    "SKU-1": {"name": "Keyboard", "price": 49.99},
    "SKU-2": {"name": "Mouse", "price": 19.99},
}


def get_product(sku):
    return PRODUCTS.get(sku)
