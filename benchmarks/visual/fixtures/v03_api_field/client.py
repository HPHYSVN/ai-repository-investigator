from api import product_response

def displayed_price():
    data = product_response()
    return data["price"]
