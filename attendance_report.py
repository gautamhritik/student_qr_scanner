from __future__ import annotations

import argparse
from pathlib import Path

from student_qr_scanner.attendance import export_attendance_report

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create attendance reports from student roster and scan history."
    )
    parser.add_argument(
        "--roster",
        type=Path,
        default=ROOT / "data" / "students.json",
        help="Student roster JSON file.",
    )
    parser.add_argument(
        "--database-dir",
        type=Path,
        default=ROOT / "scan_database",
        help="Folder containing scan_history.json.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "exports",
        help="Folder where attendance report files will be written.",
    )
    parser.add_argument("--date-from", default=None, help="Only include scans on or after YYYY-MM-DD.")
    parser.add_argument("--date-to", default=None, help="Only include scans on or before YYYY-MM-DD.")
    parser.add_argument("--class-name", default=None, help="Only report students in this class.")
    args = parser.parse_args()

    outputs = export_attendance_report(
        args.roster,
        args.database_dir,
        args.output_dir,
        date_from=args.date_from,
        date_to=args.date_to,
        student_class=args.class_name,
    )
    print(f"Attendance CSV: {outputs['csv']}")
    print(f"Attendance summary: {outputs['summary']}")
    print(f"Attendance HTML report: {outputs['html']}")


if __name__ == "__main__":
    main()
