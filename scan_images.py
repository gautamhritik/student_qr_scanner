from __future__ import annotations

import argparse
from pathlib import Path

from mining_qr_scanner.gate_registry import validate_scanner_assignment
from mining_qr_scanner.mining_events import MiningEventStore
from mining_qr_scanner.offline_scan import collect_image_paths, scan_image_paths

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan mining vehicle QR codes from saved image files.")
    parser.add_argument("inputs", nargs="+", type=Path, help="Image files or folders to scan.")
    parser.add_argument("--site-id", default="mine-1")
    parser.add_argument("--gate-id", default="main-gate")
    parser.add_argument("--checkpoint-id", default="gate-1")
    parser.add_argument("--camera-id", default="pole-cam-1")
    parser.add_argument("--direction", choices=["in", "out"], required=True)
    parser.add_argument("--database-dir", type=Path, default=ROOT / "mining_database")
    parser.add_argument("--gate-registry", type=Path, default=ROOT / "data" / "gates.json")
    parser.add_argument("--skip-gate-validation", action="store_true")
    parser.add_argument("--save-failures", action="store_true", help="Store image read failures and no-QR detections.")
    parser.add_argument("--anpr-plate-number", help="Optional ANPR placeholder value to compare with QR plate.")
    args = parser.parse_args()

    if not args.skip_gate_validation:
        try:
            validate_scanner_assignment(
                args.gate_registry,
                site_id=args.site_id,
                gate_id=args.gate_id,
                checkpoint_id=args.checkpoint_id,
                camera_id=args.camera_id,
                direction=args.direction,
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc

    image_paths = collect_image_paths(args.inputs)
    if not image_paths:
        raise SystemExit("No supported image files found.")

    store = MiningEventStore(args.database_dir)
    records = scan_image_paths(
        image_paths,
        store,
        site_id=args.site_id,
        gate_id=args.gate_id,
        checkpoint_id=args.checkpoint_id,
        camera_id=args.camera_id,
        direction=args.direction,
        save_failures=args.save_failures,
        anpr_plate_number=args.anpr_plate_number,
    )
    accepted = sum(1 for record in records if record.get("scan_status") == "accepted")
    print(f"Scanned {len(image_paths)} images; stored {len(records)} events; accepted {accepted}.")


if __name__ == "__main__":
    main()
