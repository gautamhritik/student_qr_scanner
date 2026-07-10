from __future__ import annotations

import argparse
from pathlib import Path

from mining_qr_scanner.trips import export_trips

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconstruct and export mining vehicle trips from in/out events.")
    parser.add_argument(
        "--database-dir",
        type=Path,
        default=ROOT / "mining_database",
        help="Folder containing mining movement events.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "exports",
        help="Folder where trip CSV/JSON/HTML reports are written.",
    )
    parser.add_argument("--date-from", help="Keep trips on or after YYYY-MM-DD.")
    parser.add_argument("--date-to", help="Keep trips on or before YYYY-MM-DD.")
    parser.add_argument("--vehicle-id", help="Filter by vehicle ID.")
    parser.add_argument("--material-type", help="Filter by exact material type.")
    parser.add_argument("--route-id", help="Filter by exact route ID.")
    parser.add_argument(
        "--trip-status",
        choices=["completed", "open", "missing_out", "orphan_out"],
        help="Filter by reconstructed trip status.",
    )
    args = parser.parse_args()

    outputs = export_trips(
        args.database_dir,
        args.output_dir,
        date_from=args.date_from,
        date_to=args.date_to,
        vehicle_id=args.vehicle_id,
        material_type=args.material_type,
        route_id=args.route_id,
        trip_status=args.trip_status,
    )
    print("Exported mining trip reports:")
    for label, path in outputs.items():
        print(f"- {label}: {path}")


if __name__ == "__main__":
    main()
