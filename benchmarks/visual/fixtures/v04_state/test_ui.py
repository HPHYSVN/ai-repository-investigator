from ui import on_add_clicked

def test_add_updates_state():
    s = on_add_clicked({"items": []}, "book")
    assert s["items"] == ["book"]
