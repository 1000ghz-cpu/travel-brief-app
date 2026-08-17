from .storage import load_tasks, save_tasks

PRIORITIES = ("low", "medium", "high")
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def add_task(description, priority="medium"):
    if priority not in PRIORITIES:
        raise ValueError(f"priority must be one of {PRIORITIES}")
    tasks = load_tasks()
    next_id = max((task["id"] for task in tasks), default=0) + 1
    tasks.append({"id": next_id, "description": description, "done": False, "priority": priority})
    save_tasks(tasks)
    return next_id


def list_tasks():
    tasks = load_tasks()
    return sorted(tasks, key=lambda task: PRIORITY_ORDER.get(task.get("priority", "medium"), 1))


def mark_done(task_id):
    tasks = load_tasks()
    for task in tasks:
        if task["id"] == task_id:
            task["done"] = True
            save_tasks(tasks)
            return True
    return False


def delete_task(task_id):
    tasks = load_tasks()
    remaining = [task for task in tasks if task["id"] != task_id]
    if len(remaining) == len(tasks):
        return False
    save_tasks(remaining)
    return True
