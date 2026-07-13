from __future__ import annotations

import argparse
from pathlib import Path

from mining_qr_scanner.shift_reports import export_shift_report

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Export day/night mining shift summaries.")
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
        help="Folder where shift report files are written.",
    )
    parser.add_argument("--date-from", help="Keep shifts from events/trips on or after YYYY-MM-DD.")
    parser.add_argument("--date-to", help="Keep shifts from events/trips on or before YYYY-MM-DD.")
    parser.add_argument(
        "--day-start-hour",
        type=int,
        default=6,
        help="Hour when day shift starts, from 0 to 23.",
    )
    parser.add_argument(
        "--night-start-hour",
        type=int,
        default=18,
        help="Hour when night shift starts, from 0 to 23.",
    )
    args = parser.parse_args()

    try:
        outputs = export_shift_report(
            args.database_dir,
            args.output_dir,
            date_from=args.date_from,
            date_to=args.date_to,
            day_start_hour=args.day_start_hour,
            night_start_hour=args.night_start_hour,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    print("Exported mining shift report:")
    for label, path in outputs.items():
        print(f"- {label}: {path}")


if __name__ == "__main__":
    main()
