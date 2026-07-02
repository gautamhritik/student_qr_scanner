from __future__ import annotations

import argparse
from pathlib import Path

from student_qr_scanner.reports import export_scan_database

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export QR scan history to CSV, summary JSON, and HTML."
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
        help="Folder where export files will be written.",
    )
    parser.add_argument("--date-from", default=None, help="Only include scans on or after YYYY-MM-DD.")
    parser.add_argument("--date-to", default=None, help="Only include scans on or before YYYY-MM-DD.")
    parser.add_argument("--student-name", default=None, help="Only include scans matching this student name.")
    parser.add_argument("--class-name", default=None, help="Only include scans for this class.")
    args = parser.parse_args()

    outputs = export_scan_database(
        args.database_dir,
        args.output_dir,
        date_from=args.date_from,
        date_to=args.date_to,
        student_name=args.student_name,
        student_class=args.class_name,
    )
    print(f"CSV export: {outputs['csv']}")
    print(f"Summary export: {outputs['summary']}")
    print(f"HTML report: {outputs['html']}")


if __name__ == "__main__":
    main()
