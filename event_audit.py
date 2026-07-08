from __future__ import annotations

import argparse
from pathlib import Path

from mining_qr_scanner.audit import (
    audit_events,
    write_audit_csv,
    write_audit_html,
    write_audit_json,
)
from mining_qr_scanner.mining_events import MiningEventStore

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit mining vehicle movement events for operational anomalies.")
    parser.add_argument(
        "--database-dir",
        type=Path,
        default=ROOT / "mining_database",
        help="Folder containing events.json and vehicle_state.json.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "exports",
        help="Folder where audit JSON/CSV/HTML files are written.",
    )
    parser.add_argument(
        "--stale-inside-hours",
        type=float,
        default=12.0,
        help="Flag vehicles still inside after this many hours.",
    )
    parser.add_argument(
        "--rebuild-state",
        action="store_true",
        help="Rebuild vehicle_state.json from accepted movement events before auditing.",
    )
    args = parser.parse_args()

    if args.stale_inside_hours <= 0:
        raise SystemExit("--stale-inside-hours must be greater than 0.")

    store = MiningEventStore(args.database_dir)
    vehicle_state = store.rebuild_vehicle_state() if args.rebuild_state else store.load_vehicle_state()
    report = audit_events(
        store.load_events(),
        vehicle_state,
        stale_inside_hours=args.stale_inside_hours,
    )
    outputs = {
        "json": write_audit_json(report, args.output_dir / "movement_audit.json"),
        "csv": write_audit_csv(report, args.output_dir / "movement_audit.csv"),
        "html": write_audit_html(report, args.output_dir / "movement_audit.html"),
    }

    print(f"Audit complete: {report['total_issues']} issues across {report['total_events']} events.")
    for label, path in outputs.items():
        print(f"- {label}: {path}")


if __name__ == "__main__":
    main()
