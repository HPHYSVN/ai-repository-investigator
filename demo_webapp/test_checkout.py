import pytest
from cart_api import checkout

def test_known_items():
    assert checkout([("SKU-1", 1)]) == {"total": "$49.99"}

def test_unknown_sku_raises_clear_error():
    with pytest.raises(ValueError):
        checkout([("SKU-GIFT", 1)])
