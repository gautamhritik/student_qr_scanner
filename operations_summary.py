from __future__ import annotations

import argparse
from pathlib import Path

from mining_qr_scanner.operations import export_operations_summary

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a mining operations summary dashboard.")
    parser.add_argument(
        "--database-dir",
        type=Path,
        default=ROOT / "mining_database",
        help="Folder containing mining events and vehicle_state.json.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "exports",
        help="Folder where operations summary files are written.",
    )
    parser.add_argument("--date-from", help="Keep events/trips on or after YYYY-MM-DD.")
    parser.add_argument("--date-to", help="Keep events/trips on or before YYYY-MM-DD.")
    parser.add_argument(
        "--stale-inside-hours",
        type=float,
        default=12.0,
        help="Flag vehicles still inside after this many hours.",
    )
    parser.add_argument(
        "--skip-environment",
        action="store_true",
        help="Do not include OpenCV environment diagnostics in the summary.",
    )
    args = parser.parse_args()
    if args.stale_inside_hours <= 0:
        raise SystemExit("--stale-inside-hours must be greater than 0.")

    outputs = export_operations_summary(
        args.database_dir,
        args.output_dir,
        date_from=args.date_from,
        date_to=args.date_to,
        include_environment=not args.skip_environment,
        stale_inside_hours=args.stale_inside_hours,
    )
    print("Exported mining operations summary:")
    for label, path in outputs.items():
        print(f"- {label}: {path}")


if __name__ == "__main__":
    main()
