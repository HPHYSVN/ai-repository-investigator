PRODUCTS = {
    "SKU-1": {"name": "Mechanical Keyboard", "price": 49.99},
    "SKU-2": {"name": "Wireless Mouse", "price": 19.99},
}

def get_product(sku):
    return PRODUCTS.get(sku)
