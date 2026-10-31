from todo import add_task, open_tasks

def test_add():
    assert len(open_tasks(add_task([], "x"))) == 1
