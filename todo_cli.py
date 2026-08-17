#!/usr/bin/env python3
import argparse

from todo.tasks import add_task, list_tasks, mark_done


def cmd_add(args):
    task_id = add_task(args.description)
    print(f"Added task {task_id}: {args.description}")


def cmd_list(args):
    tasks = list_tasks()
    if not tasks:
        print("No tasks yet.")
        return
    for task in tasks:
        status = "x" if task["done"] else " "
        print(f"[{status}] {task['id']}: {task['description']}")


def cmd_done(args):
    if mark_done(args.id):
        print(f"Marked task {args.id} as done.")
    else:
        print(f"No task found with id {args.id}.")


def main():
    parser = argparse.ArgumentParser(description="Simple command-line to-do list.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a new task")
    add_parser.add_argument("description", help="Task description")
    add_parser.set_defaults(func=cmd_add)

    list_parser = subparsers.add_parser("list", help="List all tasks")
    list_parser.set_defaults(func=cmd_list)

    done_parser = subparsers.add_parser("done", help="Mark a task as done")
    done_parser.add_argument("id", type=int, help="Task id")
    done_parser.set_defaults(func=cmd_done)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
