from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from mining_qr_scanner.mining_events import MiningEventStore
from mining_qr_scanner.mining_reports import summarize_vehicle_state

ROOT = Path(__file__).resolve().parent

STATE_FIELDS = [
    "vehicle_id",
    "plate_number",
    "current_status",
    "last_scan_at",
    "last_direction",
    "last_gate_id",
    "last_checkpoint_id",
    "last_camera_id",
    "driver_id",
    "driver_name",
    "material_type",
    "load_status",
    "load_weight_tons",
    "route_id",
    "source_zone",
    "destination_zone",
]


def filter_state(
    vehicle_state: dict,
    *,
    status: str | None = None,
    gate_id: str | None = None,
    material_type: str | None = None,
) -> list[dict]:
    status_query = status.casefold() if status else None
    gate_query = gate_id.casefold() if gate_id else None
    material_query = material_type.casefold() if material_type else None
    rows = []
    for item in vehicle_state.values():
        if status_query and item.get("current_status", "").casefold() != status_query:
            continue
        if gate_query and item.get("last_gate_id", "").casefold() != gate_query:
            continue
        if material_query and item.get("material_type", "").casefold() != material_query:
            continue
        rows.append({field: item.get(field, "") for field in STATE_FIELDS})
    return sorted(rows, key=lambda row: (row["current_status"], row["vehicle_id"]))


def write_state_csv(rows: list[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=STATE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Show current mining vehicle inside/outside status.")
    parser.add_argument(
        "--database-dir",
        type=Path,
        default=ROOT / "mining_database",
        help="Folder containing mining movement events and vehicle_state.json.",
    )
    parser.add_argument("--status", choices=["inside", "outside", "unknown"], help="Filter by current vehicle status.")
    parser.add_argument("--gate-id", help="Filter by last gate ID.")
    parser.add_argument("--material-type", help="Filter by current material type.")
    parser.add_argument("--json", action="store_true", help="Print filtered rows as JSON.")
    parser.add_argument("--csv-output", type=Path, help="Write filtered rows to a CSV file.")
    args = parser.parse_args()

    store = MiningEventStore(args.database_dir)
    vehicle_state = store.load_vehicle_state()
    rows = filter_state(
        vehicle_state,
        status=args.status,
        gate_id=args.gate_id,
        material_type=args.material_type,
    )
    summary = summarize_vehicle_state(vehicle_state)

    if args.json:
        print(json.dumps({"summary": summary, "vehicles": rows}, ensure_ascii=False, indent=2))
    else:
        print(
            "Current vehicles: "
            f"{summary['inside']} inside, {summary['outside']} outside, "
            f"{summary['unknown']} unknown, {summary['total_tracked_vehicles']} tracked"
        )
        print("vehicle | status | plate | driver | material | last gate | last scan")
        for row in rows:
            print(
                " | ".join(
                    [
                        row["vehicle_id"],
                        row["current_status"],
                        row["plate_number"],
                        row["driver_name"],
                        row["material_type"],
                        row["last_gate_id"],
                        row["last_scan_at"],
                    ]
                )
            )
        print(f"Rows shown: {len(rows)}")

    if args.csv_output:
        path = write_state_csv(rows, args.csv_output)
        print(f"Wrote vehicle status CSV: {path}")


if __name__ == "__main__":
    main()
