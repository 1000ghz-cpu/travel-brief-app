#!/usr/bin/env python3
import argparse

from todo.tasks import PRIORITIES, add_task, delete_task, list_tasks, mark_done


def cmd_add(args):
    task_id = add_task(args.description, args.priority)
    print(f"Added task {task_id}: {args.description} ({args.priority})")


def cmd_list(args):
    tasks = list_tasks()
    if not tasks:
        print("No tasks yet.")
        return
    for task in tasks:
        status = "x" if task["done"] else " "
        priority = task.get("priority", "medium")
        print(f"[{status}] {task['id']}: {task['description']} ({priority})")


def cmd_done(args):
    if mark_done(args.id):
        print(f"Marked task {args.id} as done.")
    else:
        print(f"No task found with id {args.id}.")


def cmd_delete(args):
    if delete_task(args.id):
        print(f"Deleted task {args.id}.")
    else:
        print(f"No task found with id {args.id}.")


def main():
    parser = argparse.ArgumentParser(description="Simple command-line to-do list.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a new task")
    add_parser.add_argument("description", help="Task description")
    add_parser.add_argument(
        "-p", "--priority", choices=PRIORITIES, default="medium", help="Task priority (default: medium)"
    )
    add_parser.set_defaults(func=cmd_add)

    list_parser = subparsers.add_parser("list", help="List all tasks")
    list_parser.set_defaults(func=cmd_list)

    done_parser = subparsers.add_parser("done", help="Mark a task as done")
    done_parser.add_argument("id", type=int, help="Task id")
    done_parser.set_defaults(func=cmd_done)

    delete_parser = subparsers.add_parser("delete", help="Delete a task")
    delete_parser.add_argument("id", type=int, help="Task id")
    delete_parser.set_defaults(func=cmd_delete)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
