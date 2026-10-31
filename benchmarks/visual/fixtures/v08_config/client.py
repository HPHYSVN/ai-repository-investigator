from settings import CONFIG

def request_timeout():
    return CONFIG.get("request_timeout")
