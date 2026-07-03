from __future__ import annotations

import csv
from html import escape
import json
from pathlib import Path
from typing import Iterable

from student_qr_scanner.reports import filter_records, flatten_record
from student_qr_scanner.storage import ScanDatabase

ATTENDANCE_FIELDS = [
    "name",
    "class",
    "roll_no",
    "age",
    "class_teacher",
    "status",
    "scan_count",
    "first_scan_at",
    "last_scan_at",
]


def load_roster(roster_path: Path) -> list[dict]:
    if not roster_path.exists():
        raise FileNotFoundError(f"Roster file not found: {roster_path}")

    roster = json.loads(roster_path.read_text(encoding="utf-8"))
    if not isinstance(roster, list):
        raise ValueError("Roster JSON must contain a list of students.")
    return [student for student in roster if isinstance(student, dict)]


def student_key(student: dict) -> tuple[str, str, str]:
    return (
        str(student.get("name", "")).casefold().strip(),
        str(student.get("class", "")).casefold().strip(),
        str(student.get("roll_no", "")).casefold().strip(),
    )


def build_attendance_rows(roster: Iterable[dict], records: Iterable[dict]) -> list[dict]:
    scans_by_student: dict[tuple[str, str, str], list[dict]] = {}
    for record in records:
        flat = flatten_record(record)
        key = student_key(
            {
                "name": flat["name"],
                "class": flat["class"],
                "roll_no": flat["roll_no"],
            }
        )
        scans_by_student.setdefault(key, []).append(flat)

    rows = []
    for student in roster:
        key = student_key(student)
        scans = sorted(
            scans_by_student.get(key, []),
            key=lambda scan: scan["scanned_at"],
        )
        row = {
            "name": student.get("name", ""),
            "class": student.get("class", ""),
            "roll_no": student.get("roll_no", ""),
            "age": student.get("age", ""),
            "class_teacher": student.get("class_teacher", ""),
            "status": "present" if scans else "absent",
            "scan_count": len(scans),
            "first_scan_at": scans[0]["scanned_at"] if scans else "",
            "last_scan_at": scans[-1]["scanned_at"] if scans else "",
        }
        rows.append(row)

    return rows


def summarize_attendance(rows: Iterable[dict]) -> dict:
    row_list = list(rows)
    present = [row for row in row_list if row["status"] == "present"]
    absent = [row for row in row_list if row["status"] == "absent"]
    return {
        "total_students": len(row_list),
        "present": len(present),
        "absent": len(absent),
        "present_students": [row["name"] for row in present],
        "absent_students": [row["name"] for row in absent],
    }


def write_attendance_csv(rows: Iterable[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=ATTENDANCE_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in ATTENDANCE_FIELDS})
    return output_path


def write_attendance_summary(rows: Iterable[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summarize_attendance(rows), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def write_attendance_html(rows: Iterable[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    row_list = list(rows)
    summary = summarize_attendance(row_list)

    table_rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(row['name']))}</td>"
        f"<td>{escape(str(row['class']))}</td>"
        f"<td>{escape(str(row['roll_no']))}</td>"
        f"<td>{escape(str(row['status']))}</td>"
        f"<td>{escape(str(row['scan_count']))}</td>"
        f"<td>{escape(str(row['first_scan_at']))}</td>"
        "</tr>"
        for row in row_list
    )
    if not table_rows:
        table_rows = "<tr><td colspan=\"6\">No roster students found</td></tr>"

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Student Attendance Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2937; }}
    .metrics {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 20px 0; }}
    .metric {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 12px; min-width: 140px; }}
    .metric span {{ display: block; color: #6b7280; font-size: 13px; }}
    .metric strong {{ display: block; font-size: 24px; margin-top: 4px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; }}
    th {{ background: #f3f4f6; }}
  </style>
</head>
<body>
  <h1>Student Attendance Report</h1>
  <div class="metrics">
    <div class="metric"><span>Total students</span><strong>{summary["total_students"]}</strong></div>
    <div class="metric"><span>Present</span><strong>{summary["present"]}</strong></div>
    <div class="metric"><span>Absent</span><strong>{summary["absent"]}</strong></div>
  </div>
  <table>
    <thead><tr><th>Name</th><th>Class</th><th>Roll no</th><th>Status</th><th>Scans</th><th>First scan</th></tr></thead>
    <tbody>{table_rows}</tbody>
  </table>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
    return output_path


def export_attendance_report(
    roster_path: Path,
    database_dir: Path,
    output_dir: Path,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    student_class: str | None = None,
) -> dict[str, Path]:
    roster = load_roster(roster_path)
    if student_class:
        roster = [
            student
            for student in roster
            if str(student.get("class", "")).casefold() == student_class.casefold()
        ]

    database = ScanDatabase(database_dir)
    records = filter_records(
        database.load_history(),
        date_from=date_from,
        date_to=date_to,
        student_class=student_class,
    )
    rows = build_attendance_rows(roster, records)
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = write_attendance_csv(rows, output_dir / "attendance.csv")
    summary_path = write_attendance_summary(rows, output_dir / "attendance_summary.json")
    html_path = write_attendance_html(rows, output_dir / "attendance_report.html")

    return {
        "csv": csv_path,
        "summary": summary_path,
        "html": html_path,
    }
