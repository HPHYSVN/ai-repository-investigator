def add_task(tasks, title):
    tasks.append({"title": title, "done": False})
    return tasks

def open_tasks(tasks):
    return [t for t in tasks if not t["done"]]
