from .storage import load_tasks, save_tasks


def add_task(description):
    tasks = load_tasks()
    next_id = max((task["id"] for task in tasks), default=0) + 1
    tasks.append({"id": next_id, "description": description, "done": False})
    save_tasks(tasks)
    return next_id


def list_tasks():
    return load_tasks()


def mark_done(task_id):
    tasks = load_tasks()
    for task in tasks:
        if task["id"] == task_id:
            task["done"] = True
            save_tasks(tasks)
            return True
    return False
