from __future__ import annotations

import csv
import json

from generate_qrs import generate_qr_files, qr_payload, write_student_data


def student() -> dict:
    return {
        "name": "Aarav Mehta",
        "class": "8A",
        "roll_no": 11,
        "age": 13,
        "class_teacher": "Mrs. Kavita Sharma",
    }


def test_qr_payload_is_compact_json() -> None:
    payload = qr_payload(student())

    assert json.loads(payload)["name"] == "Aarav Mehta"
    assert ", " not in payload
    assert ": " not in payload


def test_write_student_data_writes_json_and_csv(tmp_path) -> None:
    write_student_data([student()], tmp_path)

    assert json.loads((tmp_path / "students.json").read_text(encoding="utf-8")) == [
        student()
    ]
    with (tmp_path / "students.csv").open("r", encoding="utf-8", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))
    assert rows[0]["name"] == "Aarav Mehta"


def test_generate_qr_files_clears_old_pngs_and_writes_both_sizes(tmp_path) -> None:
    qr_dir = tmp_path / "qrs"
    large_qr_dir = tmp_path / "large"
    qr_dir.mkdir()
    large_qr_dir.mkdir()
    (qr_dir / "old.png").write_bytes(b"old")
    (large_qr_dir / "old.png").write_bytes(b"old")

    generate_qr_files([student()], qr_dir, large_qr_dir)

    assert not (qr_dir / "old.png").exists()
    assert not (large_qr_dir / "old.png").exists()
    assert len(list(qr_dir.glob("*.png"))) == 1
    assert len(list(large_qr_dir.glob("*.png"))) == 1
