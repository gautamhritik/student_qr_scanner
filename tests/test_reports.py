from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from student_qr_scanner.reports import (
    export_scan_database,
    filter_records,
    flatten_record,
    summarize_records,
    write_html_report,
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


def test_filter_records_by_date_name_and_class() -> None:
    records = [
        make_record("Aarav Mehta", "8A"),
        make_record("Isha Rao", "7B", "2026-07-02"),
        make_record("Arjun Malhotra", "9A", "2026-07-03"),
    ]

    filtered = filter_records(
        records,
        date_from="2026-07-02",
        date_to="2026-07-03",
        student_name="arjun",
        student_class="9A",
    )

    assert [record["qr_info"]["name"] for record in filtered] == ["Arjun Malhotra"]


def test_write_csv_creates_spreadsheet_ready_file(tmp_path: Path) -> None:
    output_path = write_csv([make_record("Aarav Mehta", "8A")], tmp_path / "scan.csv")

    with output_path.open("r", encoding="utf-8", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert rows[0]["name"] == "Aarav Mehta"
    assert rows[0]["class"] == "8A"


def test_write_html_report_creates_browser_report(tmp_path: Path) -> None:
    output_path = write_html_report(
        [make_record("Aarav Mehta", "8A")],
        tmp_path / "scan_report.html",
    )

    html = output_path.read_text(encoding="utf-8")
    assert "Student QR Scan Report" in html
    assert "Aarav Mehta" in html
    assert "Total scans" in html


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
    assert outputs["html"].exists()
    summary = json.loads(outputs["summary"].read_text(encoding="utf-8"))
    assert summary["total_scans"] == 1
    assert summary["by_student"] == {"Aarav Mehta": 1}


def test_export_scan_database_applies_filters(tmp_path: Path) -> None:
    database = ScanDatabase(tmp_path / "scan_database")
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
        datetime(2026, 7, 1, 10, 30, 5, tzinfo=timezone.utc),
    )
    database.save_scan(
        json.dumps(
            {
                "name": "Isha Rao",
                "class": "7B",
                "roll_no": 4,
                "age": 12,
                "class_teacher": "Mr. Rohan Menon",
            }
        ),
        "unit-test",
        datetime(2026, 7, 2, 10, 30, 5, tzinfo=timezone.utc),
    )

    outputs = export_scan_database(
        tmp_path / "scan_database",
        tmp_path / "exports",
        date_from="2026-07-02",
        student_class="7B",
    )

    summary = json.loads(outputs["summary"].read_text(encoding="utf-8"))
    assert summary["total_scans"] == 1
    assert summary["by_student"] == {"Isha Rao": 1}
