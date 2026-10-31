from state import add_item

def on_add_clicked(state, item):
    add_item(state, item)
    return state
