from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import qrcode

from student_qr_scanner.fleet import FLEET_FIELDS, load_fleet

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
REGISTRY_PATH = DATA_DIR / "fleet.json"
QR_DIR = ROOT / "vehicle_qrs"
LARGE_QR_DIR = ROOT / "vehicle_qrs_large_print"


def qr_payload(vehicle: dict) -> str:
    return json.dumps(vehicle, ensure_ascii=False, separators=(",", ":"))


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


def remove_old_pngs(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for png_path in output_dir.glob("*.png"):
        png_path.unlink()


def write_fleet_data(fleet: list[dict], data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    with (data_dir / "fleet.csv").open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FLEET_FIELDS)
        writer.writeheader()
        writer.writerows(fleet)


def generate_vehicle_qr_files(
    fleet: list[dict],
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

    for index, vehicle in enumerate(fleet, start=1):
        slug = vehicle["vehicle_id"].lower().replace(" ", "_")
        payload = qr_payload(vehicle)
        make_qr(payload, qr_dir / f"{index:02d}_{slug}.png")
        make_qr(
            payload,
            large_qr_dir / f"{index:02d}_{slug}_large_print.png",
            box_size=36,
            border=8,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate mining vehicle/equipment QR code images.")
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH, help="Fleet registry JSON path.")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR, help="Output folder for fleet.csv.")
    parser.add_argument("--qr-dir", type=Path, default=QR_DIR, help="Output folder for standard vehicle QR images.")
    parser.add_argument(
        "--large-qr-dir",
        type=Path,
        default=LARGE_QR_DIR,
        help="Output folder for large-print vehicle QR images.",
    )
    parser.add_argument(
        "--keep-old",
        action="store_true",
        help="Do not remove existing PNG files before generating new QR codes.",
    )
    args = parser.parse_args()

    fleet = load_fleet(args.registry)
    write_fleet_data(fleet, args.data_dir)
    generate_vehicle_qr_files(
        fleet,
        args.qr_dir,
        args.large_qr_dir,
        clear_existing=not args.keep_old,
    )
    print(f"Created {len(fleet)} vehicle/equipment QR codes in {args.qr_dir}")
    print(f"Created large-print vehicle/equipment QR codes in {args.large_qr_dir}")


if __name__ == "__main__":
    main()
