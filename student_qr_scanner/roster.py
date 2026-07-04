from __future__ import annotations

import json
from pathlib import Path

from student_qr_scanner.students import STUDENTS

REQUIRED_FIELDS = ["name", "class", "roll_no", "age", "class_teacher"]


def normalize_student(student: dict) -> dict:
    normalized = {
        "name": str(student.get("name", "")).strip(),
        "class": str(student.get("class", "")).strip(),
        "roll_no": int(student.get("roll_no", 0)),
        "age": int(student.get("age", 0)),
        "class_teacher": str(student.get("class_teacher", "")).strip(),
    }
    missing = [field for field in REQUIRED_FIELDS if not normalized.get(field)]
    if missing:
        raise ValueError(f"Missing student field(s): {', '.join(missing)}")
    return normalized


def student_key(student: dict) -> tuple[str, int]:
    return (str(student.get("class", "")).casefold(), int(student.get("roll_no", 0)))


def load_roster(path: Path, *, create_from_defaults: bool = True) -> list[dict]:
    if not path.exists():
        roster = [normalize_student(student) for student in STUDENTS]
        if create_from_defaults:
            save_roster(path, roster)
        return roster

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Roster JSON must contain a list of students.")
    return [normalize_student(student) for student in data]


def save_roster(path: Path, roster: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = [normalize_student(student) for student in roster]
    path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def add_student(roster: list[dict], student: dict) -> list[dict]:
    normalized = normalize_student(student)
    key = student_key(normalized)
    if any(student_key(existing) == key for existing in roster):
        raise ValueError(
            f"Student with class {normalized['class']} and roll no {normalized['roll_no']} already exists."
        )
    return [*roster, normalized]


def remove_student(roster: list[dict], student_class: str, roll_no: int) -> tuple[list[dict], dict]:
    target = (student_class.casefold(), int(roll_no))
    kept = []
    removed = None
    for student in roster:
        if student_key(student) == target:
            removed = student
        else:
            kept.append(student)

    if removed is None:
        raise ValueError(f"No student found for class {student_class} roll no {roll_no}.")
    return kept, removed
