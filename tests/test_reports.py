from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from student_qr_scanner.reports import (
    export_scan_database,
    flatten_record,
    summarize_records,
    write_csv,
)
from student_qr_scanner.storage import ScanDatabase


def make_record(name: str, student_class: str, date: str = "2026-07-01") -> dict:
    return {
        "scan_number": 1,
        "scan_id": f"id-{name}",
        "scanned_at": f"{date}T10:30:05+00:00",
        "date": date,
        "time": "10:30:05",
        "detection_method": "unit-test",
        "qr_info": {
            "name": name,
            "class": student_class,
            "roll_no": 11,
            "age": 13,
            "class_teacher": "Mrs. Kavita Sharma",
        },
        "record_file": "record.json",
    }


def test_flatten_record_extracts_student_fields() -> None:
    flat = flatten_record(make_record("Aarav Mehta", "8A"))

    assert flat["name"] == "Aarav Mehta"
    assert flat["class"] == "8A"
    assert flat["roll_no"] == 11
    assert flat["raw_payload"] == ""


def test_summarize_records_counts_scans() -> None:
    records = [
        make_record("Aarav Mehta", "8A"),
        make_record("Aarav Mehta", "8A"),
        make_record("Isha Rao", "7B", "2026-07-02"),
    ]

    summary = summarize_records(records)

    assert summary["total_scans"] == 3
    assert summary["unique_students"] == 2
    assert summary["by_student"] == {"Aarav Mehta": 2, "Isha Rao": 1}
    assert summary["by_class"] == {"7B": 1, "8A": 2}
    assert summary["by_date"] == {"2026-07-01": 2, "2026-07-02": 1}


def test_write_csv_creates_spreadsheet_ready_file(tmp_path: Path) -> None:
    output_path = write_csv([make_record("Aarav Mehta", "8A")], tmp_path / "scan.csv")

    with output_path.open("r", encoding="utf-8", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert rows[0]["name"] == "Aarav Mehta"
    assert rows[0]["class"] == "8A"


def test_export_scan_database_writes_csv_and_summary(tmp_path: Path) -> None:
    database = ScanDatabase(tmp_path / "scan_database")
    scanned_at = datetime(2026, 7, 1, 10, 30, 5, tzinfo=timezone.utc)
    database.save_scan(
        json.dumps(
            {
                "name": "Aarav Mehta",
                "class": "8A",
                "roll_no": 11,
                "age": 13,
                "class_teacher": "Mrs. Kavita Sharma",
            }
        ),
        "unit-test",
        scanned_at,
    )

    outputs = export_scan_database(tmp_path / "scan_database", tmp_path / "exports")

    assert outputs["csv"].exists()
    assert outputs["summary"].exists()
    summary = json.loads(outputs["summary"].read_text(encoding="utf-8"))
    assert summary["total_scans"] == 1
    assert summary["by_student"] == {"Aarav Mehta": 1}
