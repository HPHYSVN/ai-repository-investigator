def add_item(state, item):
    new_state = dict(state)
    new_state["items"] = state["items"] + [item]
    return new_state
