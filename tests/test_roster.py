from __future__ import annotations

import json

import pytest

from student_qr_scanner.roster import (
    add_student,
    load_roster,
    normalize_student,
    remove_student,
    save_roster,
)


def student(name: str = "Aarav Mehta", roll_no: int = 11) -> dict:
    return {
        "name": name,
        "class": "8A",
        "roll_no": roll_no,
        "age": 13,
        "class_teacher": "Mrs. Kavita Sharma",
    }


def test_normalize_student_trims_and_casts_values() -> None:
    normalized = normalize_student(
        {
            "name": " Aarav Mehta ",
            "class": " 8A ",
            "roll_no": "11",
            "age": "13",
            "class_teacher": " Mrs. Kavita Sharma ",
        }
    )

    assert normalized == student()


def test_add_student_rejects_duplicate_class_roll_number() -> None:
    roster = [student()]

    with pytest.raises(ValueError):
        add_student(roster, student("Another Student"))


def test_remove_student_returns_updated_roster_and_removed_student() -> None:
    roster = [student(), student("Isha Rao", 12)]

    updated, removed = remove_student(roster, "8A", 11)

    assert removed["name"] == "Aarav Mehta"
    assert [entry["name"] for entry in updated] == ["Isha Rao"]


def test_save_and_load_roster_round_trip(tmp_path) -> None:
    roster_path = tmp_path / "students.json"

    save_roster(roster_path, [student()])

    assert json.loads(roster_path.read_text(encoding="utf-8"))[0]["name"] == "Aarav Mehta"
    assert load_roster(roster_path) == [student()]


def test_load_roster_creates_defaults_when_missing(tmp_path) -> None:
    roster_path = tmp_path / "students.json"

    roster = load_roster(roster_path)

    assert roster_path.exists()
    assert len(roster) == 10
