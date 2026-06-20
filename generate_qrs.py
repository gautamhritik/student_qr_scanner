from __future__ import annotations

import csv
import json
from pathlib import Path

import qrcode

from student_qr_scanner.students import STUDENTS

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
QR_DIR = ROOT / "qrs"
LARGE_QR_DIR = ROOT / "qrs_large_print"


def qr_payload(student: dict) -> str:
    return json.dumps(student, ensure_ascii=False, separators=(",", ":"))


def make_qr(payload: str, output_path: Path, box_size: int = 12, border: int = 4) -> None:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    image.save(output_path)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    QR_DIR.mkdir(parents=True, exist_ok=True)
    LARGE_QR_DIR.mkdir(parents=True, exist_ok=True)

    with (DATA_DIR / "students.json").open("w", encoding="utf-8") as f:
        json.dump(STUDENTS, f, ensure_ascii=False, indent=2)

    with (DATA_DIR / "students.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["name", "class", "roll_no", "age", "class_teacher"]
        )
        writer.writeheader()
        writer.writerows(STUDENTS)

    for index, student in enumerate(STUDENTS, start=1):
        slug = student["name"].lower().replace(" ", "_")
        payload = qr_payload(student)
        make_qr(payload, QR_DIR / f"{index:02d}_{slug}.png")
        make_qr(
            payload,
            LARGE_QR_DIR / f"{index:02d}_{slug}_large_print.png",
            box_size=36,
            border=8,
        )

    print(f"Created {len(STUDENTS)} QR codes in {QR_DIR}")
    print(f"Created large-print QR codes in {LARGE_QR_DIR}")


if __name__ == "__main__":
    main()
