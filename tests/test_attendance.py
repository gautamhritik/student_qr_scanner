from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from student_qr_scanner.attendance import (
    build_attendance_rows,
    export_attendance_report,
    load_roster,
    summarize_attendance,
)
from student_qr_scanner.storage import ScanDatabase


def roster() -> list[dict]:
    return [
        {
            "name": "Aarav Mehta",
            "class": "8A",
            "roll_no": 11,
            "age": 13,
            "class_teacher": "Mrs. Kavita Sharma",
        },
        {
            "name": "Isha Rao",
            "class": "7B",
            "roll_no": 4,
            "age": 12,
            "class_teacher": "Mr. Rohan Menon",
        },
    ]


def record(name: str, student_class: str, roll_no: int, scanned_at: str) -> dict:
    return {
        "scan_number": 1,
        "scan_id": f"id-{name}",
        "scanned_at": scanned_at,
        "date": scanned_at[:10],
        "time": scanned_at[11:19],
        "detection_method": "unit-test",
        "qr_info": {
            "name": name,
            "class": student_class,
            "roll_no": roll_no,
            "age": 13,
            "class_teacher": "Teacher",
        },
    }


def test_build_attendance_rows_marks_present_and_absent() -> None:
    rows = build_attendance_rows(
        roster(),
        [record("Aarav Mehta", "8A", 11, "2026-07-02T10:30:05+00:00")],
    )

    assert rows[0]["status"] == "present"
    assert rows[0]["scan_count"] == 1
    assert rows[1]["status"] == "absent"


def test_summarize_attendance_counts_statuses() -> None:
    rows = build_attendance_rows(
        roster(),
        [record("Aarav Mehta", "8A", 11, "2026-07-02T10:30:05+00:00")],
    )

    summary = summarize_attendance(rows)

    assert summary["total_students"] == 2
    assert summary["present"] == 1
    assert summary["absent"] == 1
    assert summary["absent_students"] == ["Isha Rao"]


def test_load_roster_reads_students(tmp_path: Path) -> None:
    roster_path = tmp_path / "students.json"
    roster_path.write_text(json.dumps(roster()), encoding="utf-8")

    assert load_roster(roster_path)[0]["name"] == "Aarav Mehta"


def test_export_attendance_report_writes_outputs(tmp_path: Path) -> None:
    roster_path = tmp_path / "students.json"
    roster_path.write_text(json.dumps(roster()), encoding="utf-8")
    database = ScanDatabase(tmp_path / "scan_database")
    database.save_scan(
        json.dumps(roster()[0]),
        "unit-test",
        datetime(2026, 7, 2, 10, 30, 5, tzinfo=timezone.utc),
    )

    outputs = export_attendance_report(
        roster_path,
        tmp_path / "scan_database",
        tmp_path / "exports",
        date_from="2026-07-02",
        date_to="2026-07-02",
    )

    assert outputs["csv"].exists()
    assert outputs["summary"].exists()
    assert outputs["html"].exists()
    summary = json.loads(outputs["summary"].read_text(encoding="utf-8"))
    assert summary["present"] == 1
    assert summary["absent"] == 1
