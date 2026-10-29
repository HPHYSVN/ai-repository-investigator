USERS = {"u1": {"name": "Ada"}}

def get_user(user_id):
    if user_id not in USERS:
        return None
    return USERS[user_id]
