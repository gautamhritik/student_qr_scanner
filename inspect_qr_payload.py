from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

from mining_qr_scanner.mining_events import parse_vehicle_payload
from mining_qr_scanner.scanner import LightingAdaptiveQRScanner


def payload_from_image(image_path: Path) -> str:
    frame = cv2.imread(str(image_path))
    if frame is None:
        raise SystemExit(f"Could not read image: {image_path}")
    result = LightingAdaptiveQRScanner().detect(frame)
    if not result:
        raise SystemExit(f"No QR payload decoded from image: {image_path}")
    return result[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect and validate a mining vehicle QR payload.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--image", type=Path, help="QR image to decode and inspect.")
    source.add_argument("--payload-file", type=Path, help="Text file containing a raw QR payload.")
    source.add_argument("--payload", help="Raw QR payload string.")
    parser.add_argument("--json", action="store_true", help="Print structured JSON output.")
    args = parser.parse_args()

    if args.image:
        payload = payload_from_image(args.image)
    elif args.payload_file:
        payload = args.payload_file.read_text(encoding="utf-8").strip()
    else:
        payload = args.payload

    data, errors = parse_vehicle_payload(payload)
    result = {
        "valid": not errors,
        "errors": errors,
        "payload": data,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"Valid: {'yes' if result['valid'] else 'no'}")
    if errors:
        print("Errors:")
        for error in errors:
            print(f"- {error}")
    print(f"Vehicle: {data.get('vehicle_id', '')}")
    print(f"Plate: {data.get('plate_number', '')}")
    print(f"Driver: {data.get('driver_name', '')} ({data.get('driver_id', '')})")
    print(f"Material: {data.get('material_type', '')}")
    print(f"Payload ID: {data.get('payload_id', '')}")
    print(f"Expires on: {data.get('expires_on', '')}")


if __name__ == "__main__":
    main()
