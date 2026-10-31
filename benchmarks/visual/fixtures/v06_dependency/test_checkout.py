from checkout import total_label

def test_label():
    assert total_label(5) == "$5.00"
