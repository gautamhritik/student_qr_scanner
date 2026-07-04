from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import qrcode

from student_qr_scanner.roster import load_roster

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
QR_DIR = ROOT / "qrs"
LARGE_QR_DIR = ROOT / "qrs_large_print"
ROSTER_PATH = DATA_DIR / "students.json"


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


def write_student_data(students: list[dict], data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    with (data_dir / "students.json").open("w", encoding="utf-8") as f:
        json.dump(students, f, ensure_ascii=False, indent=2)

    with (data_dir / "students.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["name", "class", "roll_no", "age", "class_teacher"]
        )
        writer.writeheader()
        writer.writerows(students)


def remove_old_pngs(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for png_path in output_dir.glob("*.png"):
        png_path.unlink()


def generate_qr_files(
    students: list[dict],
    qr_dir: Path,
    large_qr_dir: Path,
    *,
    clear_existing: bool = True,
) -> None:
    if clear_existing:
        remove_old_pngs(qr_dir)
        remove_old_pngs(large_qr_dir)
    else:
        qr_dir.mkdir(parents=True, exist_ok=True)
        large_qr_dir.mkdir(parents=True, exist_ok=True)

    for index, student in enumerate(students, start=1):
        slug = student["name"].lower().replace(" ", "_")
        payload = qr_payload(student)
        make_qr(payload, qr_dir / f"{index:02d}_{slug}.png")
        make_qr(
            payload,
            large_qr_dir / f"{index:02d}_{slug}_large_print.png",
            box_size=36,
            border=8,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate student QR code images.")
    parser.add_argument("--roster", type=Path, default=ROSTER_PATH, help="Roster JSON path.")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR, help="Output folder for students.json/csv.")
    parser.add_argument("--qr-dir", type=Path, default=QR_DIR, help="Output folder for standard QR images.")
    parser.add_argument(
        "--large-qr-dir",
        type=Path,
        default=LARGE_QR_DIR,
        help="Output folder for large-print QR images.",
    )
    parser.add_argument(
        "--keep-old",
        action="store_true",
        help="Do not remove existing PNG files before generating new QR codes.",
    )
    args = parser.parse_args()

    students = load_roster(args.roster)
    write_student_data(students, args.data_dir)
    generate_qr_files(
        students,
        args.qr_dir,
        args.large_qr_dir,
        clear_existing=not args.keep_old,
    )

    print(f"Created {len(students)} QR codes in {args.qr_dir}")
    print(f"Created large-print QR codes in {args.large_qr_dir}")


if __name__ == "__main__":
    main()
