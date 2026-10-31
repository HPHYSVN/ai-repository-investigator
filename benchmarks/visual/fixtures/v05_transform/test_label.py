from label import price_label

def test_label():
    assert price_label(4999) == "$49.99"
