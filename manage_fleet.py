from __future__ import annotations

import argparse
import json
from pathlib import Path

from student_qr_scanner.fleet import FLEET_FIELDS, add_vehicle, load_fleet, remove_vehicle

ROOT = Path(__file__).resolve().parent
REGISTRY_PATH = ROOT / "data" / "fleet.json"


def print_vehicle(vehicle: dict) -> None:
    print(
        " | ".join(
            [
                vehicle["vehicle_id"],
                vehicle["plate_number"],
                vehicle["vehicle_type"],
                vehicle["owner_operator"],
                vehicle["site"],
                vehicle["assigned_route"],
                vehicle["checkpoint_id"],
                vehicle["status"],
            ]
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the mining fleet registry.")
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH, help="Fleet registry JSON path.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List vehicles/equipment in the registry.")

    add_parser = subparsers.add_parser("add", help="Add a vehicle/equipment record.")
    add_parser.add_argument("--vehicle-id", required=True)
    add_parser.add_argument("--plate-number", required=True)
    add_parser.add_argument("--vehicle-type", required=True)
    add_parser.add_argument("--owner-operator", default="")
    add_parser.add_argument("--site", default="")
    add_parser.add_argument("--assigned-route", default="")
    add_parser.add_argument("--checkpoint-id", default="")
    add_parser.add_argument("--status", default="active")

    remove_parser = subparsers.add_parser("remove", help="Remove a vehicle/equipment record.")
    remove_parser.add_argument("--vehicle-id", required=True)

    export_parser = subparsers.add_parser("json", help="Print the registry as JSON.")
    export_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")

    args = parser.parse_args()

    if args.command == "list":
        fleet = load_fleet(args.registry)
        print("vehicle_id | plate_number | type | owner/operator | site | route | checkpoint | status")
        for vehicle in fleet:
            print_vehicle(vehicle)
        print(f"Total vehicles/equipment: {len(fleet)}")
        return

    if args.command == "add":
        vehicle = {field: getattr(args, field) for field in FLEET_FIELDS}
        created = add_vehicle(args.registry, vehicle)
        print(f"Added vehicle/equipment: {created['vehicle_id']}")
        return

    if args.command == "remove":
        removed = remove_vehicle(args.registry, args.vehicle_id)
        print(f"Removed vehicle/equipment: {removed['vehicle_id']}")
        return

    if args.command == "json":
        fleet = load_fleet(args.registry)
        indent = 2 if args.pretty else None
        print(json.dumps(fleet, ensure_ascii=False, indent=indent))


if __name__ == "__main__":
    main()
