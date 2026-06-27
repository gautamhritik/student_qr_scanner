from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from student_qr_scanner.storage import ScanDatabase


def test_save_scan_writes_record_and_history(tmp_path: Path) -> None:
    database = ScanDatabase(tmp_path / "scan_database")
    payload = json.dumps(
        {
            "name": "Aarav Mehta",
            "class": "8A",
            "roll_no": 11,
            "age": 13,
            "class_teacher": "Mrs. Kavita Sharma",
        }
    )
    scanned_at = datetime(2026, 6, 27, 10, 30, 5, tzinfo=timezone.utc)

    first = database.save_scan(payload, "unit-test", scanned_at)
    second = database.save_scan(payload, "unit-test", scanned_at)

    assert first["scan_number"] == 1
    assert second["scan_number"] == 2
    assert first["date"] == "2026-06-27"
    assert first["time"] == "10:30:05"
    assert first["qr_info"]["name"] == "Aarav Mehta"
    assert Path(first["record_file"]).exists()
    assert Path(second["record_file"]).exists()

    history = database.load_history()
    assert [record["scan_number"] for record in history] == [1, 2]


def test_save_scan_preserves_raw_payload_for_invalid_json(tmp_path: Path) -> None:
    database = ScanDatabase(tmp_path / "scan_database")
    scanned_at = datetime(2026, 6, 27, 10, 30, 5, tzinfo=timezone.utc)

    record = database.save_scan("not-json", "unit-test", scanned_at)

    assert record["qr_info"] == {"raw_payload": "not-json"}
    assert "unknown_student" in Path(record["record_file"]).name


def test_load_history_returns_empty_list_for_invalid_history(tmp_path: Path) -> None:
    database = ScanDatabase(tmp_path / "scan_database")
    database.history_file.write_text("{broken json", encoding="utf-8")

    assert database.load_history() == []
