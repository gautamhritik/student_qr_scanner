from __future__ import annotations

import argparse
import json
from pathlib import Path

from mining_qr_scanner.gate_registry import GATE_FIELDS, add_gate, load_gates, remove_gate

ROOT = Path(__file__).resolve().parent
REGISTRY_PATH = ROOT / "data" / "gates.json"


def print_gate(gate: dict) -> None:
    print(
        " | ".join(
            [
                gate["site_id"],
                gate["gate_id"],
                gate["checkpoint_id"],
                gate["camera_id"],
                ",".join(gate["allowed_directions"]),
                gate["camera_role"],
                gate["status"],
                gate["location"],
            ]
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage mining gate and pole-camera registry records.")
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH, help="Gate registry JSON path.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List registered gate cameras.")

    add_parser = subparsers.add_parser("add", help="Add a gate camera record.")
    add_parser.add_argument("--site-id", required=True)
    add_parser.add_argument("--gate-id", required=True)
    add_parser.add_argument("--checkpoint-id", required=True)
    add_parser.add_argument("--camera-id", required=True)
    add_parser.add_argument("--allowed-directions", default="in,out")
    add_parser.add_argument("--camera-role", default="entry_exit")
    add_parser.add_argument("--stream-hint", default="")
    add_parser.add_argument("--location", default="")
    add_parser.add_argument("--status", default="active")
    add_parser.add_argument("--notes", default="")

    remove_parser = subparsers.add_parser("remove", help="Remove a gate camera record.")
    remove_parser.add_argument("--site-id", required=True)
    remove_parser.add_argument("--gate-id", required=True)
    remove_parser.add_argument("--checkpoint-id", required=True)
    remove_parser.add_argument("--camera-id", required=True)

    json_parser = subparsers.add_parser("json", help="Print the registry as JSON.")
    json_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")

    args = parser.parse_args()

    if args.command == "list":
        gates = load_gates(args.registry)
        print("site | gate | checkpoint | camera | directions | role | status | location")
        for gate in gates:
            print_gate(gate)
        print(f"Total gate cameras: {len(gates)}")
        return

    if args.command == "add":
        gate = {field: getattr(args, field) for field in GATE_FIELDS}
        created = add_gate(args.registry, gate)
        print(f"Added gate camera: {created['gate_id']} / {created['camera_id']}")
        return

    if args.command == "remove":
        removed = remove_gate(
            args.registry,
            site_id=args.site_id,
            gate_id=args.gate_id,
            checkpoint_id=args.checkpoint_id,
            camera_id=args.camera_id,
        )
        print(f"Removed gate camera: {removed['gate_id']} / {removed['camera_id']}")
        return

    if args.command == "json":
        gates = load_gates(args.registry)
        indent = 2 if args.pretty else None
        print(json.dumps(gates, ensure_ascii=False, indent=indent))


if __name__ == "__main__":
    main()
