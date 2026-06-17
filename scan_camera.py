from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import cv2

from student_qr_scanner.scanner import LightingAdaptiveQRScanner, format_payload
from student_qr_scanner.storage import ScanDatabase

ROOT = Path(__file__).resolve().parent


def parse_camera(value: str):
    try:
        return int(value)
    except ValueError:
        return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan student QR codes from a camera.")
    parser.add_argument("--camera", default="0", help="Camera index or stream URL.")
    parser.add_argument(
        "--save-scans",
        action="store_true",
        help="Save frames where a QR code is decoded.",
    )
    parser.add_argument(
        "--scan-cooldown",
        type=float,
        default=3.0,
        help="Seconds before the same QR can be logged again.",
    )
    args = parser.parse_args()

    cap = cv2.VideoCapture(parse_camera(args.camera))
    if not cap.isOpened():
        raise SystemExit(f"Could not open camera: {args.camera}")

    scanner = LightingAdaptiveQRScanner()
    database = ScanDatabase(ROOT / "scan_database")
    scans_dir = ROOT / "scans"
    scans_dir.mkdir(exist_ok=True)
    last_seen: dict[str, datetime] = {}

    print("Scanner started. Hold a student QR in front of the camera. Press q to quit.")
    while True:
        ok, frame = cap.read()
        if not ok:
            print("Could not read frame from camera.")
            break

        result = scanner.detect(frame)
        if result:
            payload, points, method = result
            now = datetime.now().astimezone()
            previous = last_seen.get(payload)
            can_log = (
                previous is None
                or (now - previous).total_seconds() >= args.scan_cooldown
            )

            if can_log:
                last_seen[payload] = now
                record = database.save_scan(payload, method, now)
                print(f"\nDetected with {method}:")
                print(format_payload(payload))
                print(f"Saved scan record: {record['record_file']}")

                if args.save_scans:
                    timestamp = now.strftime("%Y%m%d_%H%M%S")
                    cv2.imwrite(str(scans_dir / f"scan_{timestamp}.jpg"), frame)

            if points is not None:
                scanner.draw_detection(frame, points, method)

        cv2.imshow("Student QR Scanner", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
