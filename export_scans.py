from __future__ import annotations

import argparse
from pathlib import Path

from student_qr_scanner.reports import export_scan_database

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export QR scan history to CSV and summary JSON."
    )
    parser.add_argument(
        "--database-dir",
        type=Path,
        default=ROOT / "scan_database",
        help="Folder containing scan_history.json.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "exports",
        help="Folder where export files will be written.",
    )
    args = parser.parse_args()

    outputs = export_scan_database(args.database_dir, args.output_dir)
    print(f"CSV export: {outputs['csv']}")
    print(f"Summary export: {outputs['summary']}")


if __name__ == "__main__":
    main()
