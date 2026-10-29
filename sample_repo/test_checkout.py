import pytest

from checkout import checkout_total


def test_known_items():
    assert checkout_total([("SKU-1", 1)]) == "$49.99"


def test_unknown_sku_raises_clear_error():
    with pytest.raises(ValueError):
        checkout_total([("SKU-UNKNOWN", 1)])
