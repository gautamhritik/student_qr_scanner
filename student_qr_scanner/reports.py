from __future__ import annotations

import csv
from html import escape
import json
from collections import Counter
from pathlib import Path
from typing import Iterable

from student_qr_scanner.storage import ScanDatabase

CSV_FIELDS = [
    "scan_number",
    "scan_id",
    "scanned_at",
    "date",
    "time",
    "detection_method",
    "name",
    "class",
    "roll_no",
    "age",
    "class_teacher",
    "raw_payload",
    "record_file",
]


def flatten_record(record: dict) -> dict:
    qr_info = record.get("qr_info")
    if not isinstance(qr_info, dict):
        qr_info = {}

    flattened = {
        "scan_number": record.get("scan_number", ""),
        "scan_id": record.get("scan_id", ""),
        "scanned_at": record.get("scanned_at", ""),
        "date": record.get("date", ""),
        "time": record.get("time", ""),
        "detection_method": record.get("detection_method", ""),
        "name": qr_info.get("name", ""),
        "class": qr_info.get("class", ""),
        "roll_no": qr_info.get("roll_no", ""),
        "age": qr_info.get("age", ""),
        "class_teacher": qr_info.get("class_teacher", ""),
        "raw_payload": qr_info.get("raw_payload", ""),
        "record_file": record.get("record_file", ""),
    }
    return {field: flattened.get(field, "") for field in CSV_FIELDS}


def summarize_records(records: Iterable[dict]) -> dict:
    record_list = list(records)
    flat_records = [flatten_record(record) for record in record_list]

    names = [record["name"] for record in flat_records if record["name"]]
    classes = [record["class"] for record in flat_records if record["class"]]
    dates = [record["date"] for record in flat_records if record["date"]]
    methods = [
        record["detection_method"]
        for record in flat_records
        if record["detection_method"]
    ]
    scanned_at_values = sorted(
        record["scanned_at"] for record in flat_records if record["scanned_at"]
    )

    return {
        "total_scans": len(flat_records),
        "unique_students": len(set(names)),
        "by_student": dict(sorted(Counter(names).items())),
        "by_class": dict(sorted(Counter(classes).items())),
        "by_date": dict(sorted(Counter(dates).items())),
        "by_detection_method": dict(sorted(Counter(methods).items())),
        "first_scan_at": scanned_at_values[0] if scanned_at_values else "",
        "last_scan_at": scanned_at_values[-1] if scanned_at_values else "",
    }


def filter_records(
    records: Iterable[dict],
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    student_name: str | None = None,
    student_class: str | None = None,
) -> list[dict]:
    filtered = []
    student_query = student_name.casefold() if student_name else None
    class_query = student_class.casefold() if student_class else None

    for record in records:
        flat = flatten_record(record)
        if date_from and flat["date"] < date_from:
            continue
        if date_to and flat["date"] > date_to:
            continue
        if student_query and student_query not in flat["name"].casefold():
            continue
        if class_query and class_query != flat["class"].casefold():
            continue
        filtered.append(record)

    return filtered


def write_csv(records: Iterable[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for record in records:
            writer.writerow(flatten_record(record))
    return output_path


def write_html_report(records: Iterable[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    record_list = list(records)
    summary = summarize_records(record_list)
    flat_records = [flatten_record(record) for record in record_list]
    recent_records = sorted(
        flat_records,
        key=lambda record: record["scanned_at"],
        reverse=True,
    )[:25]

    def metric(label: str, value) -> str:
        return (
            "<div class=\"metric\">"
            f"<span>{escape(label)}</span>"
            f"<strong>{escape(str(value))}</strong>"
            "</div>"
        )

    def count_rows(values: dict) -> str:
        if not values:
            return "<tr><td colspan=\"2\">No data</td></tr>"
        return "\n".join(
            "<tr>"
            f"<td>{escape(str(label))}</td>"
            f"<td>{escape(str(count))}</td>"
            "</tr>"
            for label, count in values.items()
        )

    recent_rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(record['scanned_at']))}</td>"
        f"<td>{escape(str(record['name']))}</td>"
        f"<td>{escape(str(record['class']))}</td>"
        f"<td>{escape(str(record['roll_no']))}</td>"
        f"<td>{escape(str(record['detection_method']))}</td>"
        "</tr>"
        for record in recent_records
    )
    if not recent_rows:
        recent_rows = "<tr><td colspan=\"5\">No scan records found</td></tr>"

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Student QR Scan Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2937; }}
    h1, h2 {{ margin-bottom: 8px; }}
    .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 20px 0; }}
    .metric {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 12px; }}
    .metric span {{ display: block; color: #6b7280; font-size: 13px; }}
    .metric strong {{ display: block; font-size: 24px; margin-top: 4px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0 28px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; }}
    th {{ background: #f3f4f6; }}
  </style>
</head>
<body>
  <h1>Student QR Scan Report</h1>
  <div class="metrics">
    {metric("Total scans", summary["total_scans"])}
    {metric("Unique students", summary["unique_students"])}
    {metric("First scan", summary["first_scan_at"] or "N/A")}
    {metric("Last scan", summary["last_scan_at"] or "N/A")}
  </div>

  <h2>Scans by class</h2>
  <table><thead><tr><th>Class</th><th>Scans</th></tr></thead><tbody>{count_rows(summary["by_class"])}</tbody></table>

  <h2>Scans by date</h2>
  <table><thead><tr><th>Date</th><th>Scans</th></tr></thead><tbody>{count_rows(summary["by_date"])}</tbody></table>

  <h2>Recent scans</h2>
  <table>
    <thead><tr><th>Scanned at</th><th>Name</th><th>Class</th><th>Roll no</th><th>Method</th></tr></thead>
    <tbody>{recent_rows}</tbody>
  </table>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
    return output_path


def write_summary(records: Iterable[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary = summarize_records(records)
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def export_scan_database(
    database_dir: Path,
    output_dir: Path,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    student_name: str | None = None,
    student_class: str | None = None,
) -> dict[str, Path]:
    database = ScanDatabase(database_dir)
    records = filter_records(
        database.load_history(),
        date_from=date_from,
        date_to=date_to,
        student_name=student_name,
        student_class=student_class,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = write_csv(records, output_dir / "scan_history.csv")
    summary_path = write_summary(records, output_dir / "scan_summary.json")
    html_path = write_html_report(records, output_dir / "scan_report.html")

    return {
        "csv": csv_path,
        "summary": summary_path,
        "html": html_path,
    }
