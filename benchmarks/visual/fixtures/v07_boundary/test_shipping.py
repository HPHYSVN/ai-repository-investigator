from shipping import qualifies_for_free_shipping

def test_below():
    assert qualifies_for_free_shipping(99.99) is False

def test_exact_threshold_qualifies():
    assert qualifies_for_free_shipping(100) is True
