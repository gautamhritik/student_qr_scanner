from __future__ import annotations

import argparse
from pathlib import Path

from student_qr_scanner.roster import add_student, load_roster, remove_student, save_roster

ROOT = Path(__file__).resolve().parent
DEFAULT_ROSTER = ROOT / "data" / "students.json"


def print_roster(roster: list[dict]) -> None:
    if not roster:
        print("No students found.")
        return

    for student in roster:
        print(
            f"{student['class']} roll {student['roll_no']}: "
            f"{student['name']} ({student['age']}), teacher: {student['class_teacher']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the student QR roster.")
    parser.add_argument(
        "--roster",
        type=Path,
        default=DEFAULT_ROSTER,
        help="Path to students.json roster.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List students in the roster.")

    add_parser = subparsers.add_parser("add", help="Add a student to the roster.")
    add_parser.add_argument("--name", required=True)
    add_parser.add_argument("--class-name", required=True)
    add_parser.add_argument("--roll-no", type=int, required=True)
    add_parser.add_argument("--age", type=int, required=True)
    add_parser.add_argument("--class-teacher", required=True)

    remove_parser = subparsers.add_parser("remove", help="Remove a student by class and roll number.")
    remove_parser.add_argument("--class-name", required=True)
    remove_parser.add_argument("--roll-no", type=int, required=True)

    args = parser.parse_args()
    roster = load_roster(args.roster)

    if args.command == "list":
        print_roster(roster)
        return

    if args.command == "add":
        roster = add_student(
            roster,
            {
                "name": args.name,
                "class": args.class_name,
                "roll_no": args.roll_no,
                "age": args.age,
                "class_teacher": args.class_teacher,
            },
        )
        save_roster(args.roster, roster)
        print(f"Added {args.name}.")
        return

    if args.command == "remove":
        roster, removed = remove_student(roster, args.class_name, args.roll_no)
        save_roster(args.roster, roster)
        print(f"Removed {removed['name']}.")


if __name__ == "__main__":
    main()
