from __future__ import annotations

import csv
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


def write_csv(records: Iterable[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for record in records:
            writer.writerow(flatten_record(record))
    return output_path


def write_summary(records: Iterable[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary = summarize_records(records)
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def export_scan_database(database_dir: Path, output_dir: Path) -> dict[str, Path]:
    database = ScanDatabase(database_dir)
    records = database.load_history()
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = write_csv(records, output_dir / "scan_history.csv")
    summary_path = write_summary(records, output_dir / "scan_summary.json")

    return {
        "csv": csv_path,
        "summary": summary_path,
    }
