from __future__ import annotations

import argparse
from pathlib import Path

from student_qr_scanner.mining_reports import export_mining_events

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Export mining QR scan events.")
    parser.add_argument(
        "--database-dir",
        type=Path,
        default=ROOT / "mining_scan_database",
        help="Folder containing mining scan event JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "exports",
        help="Folder where CSV/JSON/HTML reports are written.",
    )
    parser.add_argument("--date-from", help="Keep events on or after YYYY-MM-DD.")
    parser.add_argument("--date-to", help="Keep events on or before YYYY-MM-DD.")
    parser.add_argument("--vehicle-id", help="Filter by vehicle/equipment ID.")
    parser.add_argument("--checkpoint-id", help="Filter by exact checkpoint ID.")
    parser.add_argument("--scan-status", help="Filter by exact scan status.")
    args = parser.parse_args()

    outputs = export_mining_events(
        args.database_dir,
        args.output_dir,
        date_from=args.date_from,
        date_to=args.date_to,
        vehicle_id=args.vehicle_id,
        checkpoint_id=args.checkpoint_id,
        scan_status=args.scan_status,
    )
    print("Exported mining scan reports:")
    for label, path in outputs.items():
        print(f"- {label}: {path}")


if __name__ == "__main__":
    main()
