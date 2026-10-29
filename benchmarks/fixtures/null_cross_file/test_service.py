from service import greeting

def test_known():
    assert greeting("u1") == "Hello Ada"

def test_unknown_user_gets_guest_greeting():
    assert greeting("missing") == "Hello Guest"
