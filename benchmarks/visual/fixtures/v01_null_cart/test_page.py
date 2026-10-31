from page import render_total

def test_total():
    assert render_total([10.0]) == "Total: 10.00"

def test_missing_price_shows_zero():
    assert render_total([None]) == "Total: 0.00"
