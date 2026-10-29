from client import request_timeout

def test_timeout_from_config():
    assert request_timeout() == 30
