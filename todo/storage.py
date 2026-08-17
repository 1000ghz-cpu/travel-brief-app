import json
from pathlib import Path

TASKS_FILE = Path(__file__).resolve().parent.parent / "tasks.json"


def load_tasks():
    if not TASKS_FILE.exists():
        return []
    with open(TASKS_FILE, "r") as f:
        return json.load(f)


def save_tasks(tasks):
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2)
