from store import get_user

def greeting(user_id):
    user = get_user(user_id)
    return "Hello " + user["name"]
