from __future__ import annotations

import argparse
from collections import Counter, deque
from datetime import datetime
from pathlib import Path

import cv2

from mining_qr_scanner.gate_registry import validate_scanner_assignment
from mining_qr_scanner.mining_events import MiningEventStore, build_scan_event
from mining_qr_scanner.scanner import LightingAdaptiveQRScanner, format_payload

ROOT = Path(__file__).resolve().parent
BACKENDS = {
    "auto": None,
    "any": cv2.CAP_ANY,
    "dshow": cv2.CAP_DSHOW,
    "msmf": cv2.CAP_MSMF,
    "v4l2": cv2.CAP_V4L2,
}


def parse_camera(value: str):
    try:
        return int(value)
    except ValueError:
        return value


def configure_camera(cap, width: int, height: int, fps: int, autofocus: bool) -> None:
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)

    # These properties are camera-driver dependent. Unsupported cameras simply
    # ignore them, but supported mobile/web cameras benefit from the hints.
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 1 if autofocus else 0)
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)


def open_camera(camera, backend: str):
    backend_value = BACKENDS[backend]
    if backend_value is None:
        return cv2.VideoCapture(camera)
    return cv2.VideoCapture(camera, backend_value)


def validate_args(args) -> None:
    if args.width <= 0 or args.height <= 0:
        raise SystemExit("--width and --height must be positive integers.")
    if args.fps <= 0:
        raise SystemExit("--fps must be a positive integer.")
    if args.digital_zoom < 1.0:
        raise SystemExit("--digital-zoom must be 1.0 or greater.")
    if args.scan_cooldown < 0:
        raise SystemExit("--scan-cooldown cannot be negative.")
    if args.preview_scale <= 0:
        raise SystemExit("--preview-scale must be greater than 0.")
    if args.max_scans is not None and args.max_scans <= 0:
        raise SystemExit("--max-scans must be a positive integer.")
    if args.vote_window <= 0:
        raise SystemExit("--vote-window must be a positive integer.")
    if args.min_votes <= 0:
        raise SystemExit("--min-votes must be a positive integer.")
    if args.min_votes > args.vote_window:
        raise SystemExit("--min-votes cannot be greater than --vote-window.")
    if not args.site_id.strip():
        raise SystemExit("--site-id is required.")
    if not args.gate_id.strip():
        raise SystemExit("--gate-id is required.")
    if not args.camera_id.strip():
        raise SystemExit("--camera-id is required.")
    if not args.checkpoint_id.strip():
        raise SystemExit("--checkpoint-id is required.")


def accepted_payload_from_votes(recent_payloads, payload: str, vote_window: int, min_votes: int) -> str | None:
    recent_payloads.append(payload)
    if vote_window <= 1:
        return payload
    if len(recent_payloads) < min_votes:
        return None
    value, count = Counter(recent_payloads).most_common(1)[0]
    if count >= min_votes:
        return value
    return None


def show_preview(window_name: str, frame, preview_scale: float) -> bool:
    display_frame = frame
    if preview_scale != 1.0:
        display_frame = cv2.resize(
            frame,
            None,
            fx=preview_scale,
            fy=preview_scale,
            interpolation=cv2.INTER_AREA,
        )

    try:
        cv2.imshow(window_name, display_frame)
        return True
    except cv2.error:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan mining vehicle QR codes from a pole/gate camera.")
    parser.add_argument("--camera", default="0", help="Camera index or stream URL.")
    parser.add_argument(
        "--backend",
        choices=sorted(BACKENDS),
        default="auto",
        help="OpenCV camera backend. Try dshow or msmf on Windows if a webcam fails.",
    )
    parser.add_argument("--width", type=int, default=1920, help="Requested camera width.")
    parser.add_argument("--height", type=int, default=1080, help="Requested camera height.")
    parser.add_argument("--fps", type=int, default=30, help="Requested camera FPS.")
    parser.add_argument(
        "--digital-zoom",
        type=float,
        default=1.0,
        help="Center zoom for distant QR codes. Try 2.0 or 3.0 for long distance.",
    )
    parser.add_argument(
        "--no-autofocus",
        action="store_true",
        help="Disable autofocus hint if your camera focuses better manually.",
    )
    parser.add_argument(
        "--save-scans",
        action="store_true",
        help="Save frames where a QR code is decoded.",
    )
    parser.add_argument(
        "--scan-cooldown",
        type=float,
        default=8.0,
        help="Seconds before the same vehicle QR at the same checkpoint is logged again.",
    )
    parser.add_argument(
        "--preview-scale",
        type=float,
        default=1.0,
        help="Scale the preview window. Use 0.5 for large 1080p/4K camera frames.",
    )
    parser.add_argument(
        "--max-scans",
        type=int,
        default=None,
        help="Stop automatically after this many accepted scans.",
    )
    parser.add_argument(
        "--no-preview",
        action="store_true",
        help="Run without an OpenCV preview window.",
    )
    parser.add_argument("--site-id", default="mine-1", help="Mining site identifier saved in movement events.")
    parser.add_argument("--gate-id", default="main-gate", help="Gate identifier saved in movement events.")
    parser.add_argument("--camera-id", default="pole-cam-1", help="Pole camera identifier saved in movement events.")
    parser.add_argument(
        "--checkpoint-id",
        default="gate-1",
        help="Checkpoint identifier saved in movement events.",
    )
    parser.add_argument("--direction", choices=["in", "out"], required=True, help="Vehicle movement direction for this scanner.")
    parser.add_argument(
        "--gate-registry",
        type=Path,
        default=ROOT / "data" / "gates.json",
        help="Gate/camera registry used to validate scanner assignment.",
    )
    parser.add_argument(
        "--skip-gate-validation",
        action="store_true",
        help="Allow ad-hoc scanner metadata that is not present in the gate registry.",
    )
    parser.add_argument(
        "--database-dir",
        type=Path,
        default=ROOT / "mining_database",
        help="Folder where mining movement event JSON files are stored.",
    )
    parser.add_argument(
        "--anpr-plate-number",
        help="Optional ANPR placeholder value to compare with the QR plate number.",
    )
    parser.add_argument(
        "--vote-window",
        type=int,
        default=5,
        help="Number of recent decoded frames kept for majority voting.",
    )
    parser.add_argument(
        "--min-votes",
        type=int,
        default=3,
        help="Minimum matching decoded frames required before logging.",
    )
    args = parser.parse_args()
    validate_args(args)
    gate_config = None
    if not args.skip_gate_validation:
        try:
            gate_config = validate_scanner_assignment(
                args.gate_registry,
                site_id=args.site_id,
                gate_id=args.gate_id,
                checkpoint_id=args.checkpoint_id,
                camera_id=args.camera_id,
                direction=args.direction,
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc

    cap = open_camera(parse_camera(args.camera), args.backend)
    if not cap.isOpened():
        raise SystemExit(f"Could not open camera: {args.camera} with backend: {args.backend}")

    configure_camera(cap, args.width, args.height, args.fps, not args.no_autofocus)
    scanner = LightingAdaptiveQRScanner()
    mining_store = MiningEventStore(args.database_dir)
    scans_dir = ROOT / "scans"
    scans_dir.mkdir(exist_ok=True)
    last_seen: dict[str, datetime] = {}
    recent_payloads = deque(maxlen=args.vote_window)
    saved_this_session = 0

    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print("Mining vehicle QR scanner started. Hold a vehicle QR in front of the pole camera.")
    print(
        f"Site: {args.site_id}, gate: {args.gate_id}, checkpoint: {args.checkpoint_id}, "
        f"camera: {args.camera_id}, direction: {args.direction}"
    )
    if gate_config:
        print(f"Gate registry: {gate_config['location']} ({gate_config['camera_role']})")
    else:
        print("Gate registry validation skipped.")
    print(f"Camera frame: {actual_width}x{actual_height}, digital zoom: {args.digital_zoom:g}x")
    print(f"Camera backend: {args.backend}")
    if args.vote_window > 1:
        print(f"Frame voting: {args.min_votes} matching reads within {args.vote_window} frames")
    if args.no_preview:
        print("Preview disabled. Press Ctrl+C to stop scanning.")
    else:
        print(f"Preview scale: {args.preview_scale:g}x")
    print("For 10m scanning, use a large printed QR and keep it centered in good focus.")
    preview_enabled = not args.no_preview

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Could not read frame from camera.")
                break

            frame = scanner.digital_zoom(frame, args.digital_zoom)
            result = scanner.detect(frame)
            if result:
                payload, points, method = result
                accepted_payload = accepted_payload_from_votes(
                    recent_payloads,
                    payload,
                    args.vote_window,
                    args.min_votes,
                )
                if accepted_payload is None:
                    if points is not None:
                        scanner.draw_detection(frame, points, f"{method} (voting)")
                    if preview_enabled:
                        if not show_preview("Mining Vehicle QR Scanner", frame, args.preview_scale):
                            preview_enabled = False
                            print(
                                "OpenCV preview is unavailable in this environment. "
                                "Continuing in terminal-only mode; press Ctrl+C to stop."
                            )
                    if preview_enabled and cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                    continue

                now = datetime.now().astimezone()
                duplicate_key = f"{args.checkpoint_id}:{args.direction}:{accepted_payload}"
                previous = last_seen.get(duplicate_key)
                can_log = (
                    previous is None
                    or (now - previous).total_seconds() >= args.scan_cooldown
                )

                readiness = scanner.estimate_distance_readiness(points, frame)
                frame_path = ""
                if args.save_scans and can_log:
                    timestamp = now.strftime("%Y%m%d_%H%M%S")
                    frame_path = str(scans_dir / f"{args.direction}_{timestamp}.jpg")
                    cv2.imwrite(frame_path, frame)

                if can_log:
                    last_seen[duplicate_key] = now
                    scan_status = None
                else:
                    scan_status = "duplicate_suppressed"

                event = build_scan_event(
                    accepted_payload,
                    method,
                    now,
                    site_id=args.site_id,
                    gate_id=args.gate_id,
                    camera_id=args.camera_id,
                    checkpoint_id=args.checkpoint_id,
                    direction=args.direction,
                    readiness=readiness,
                    vote_window=args.vote_window,
                    min_votes=args.min_votes,
                    vote_count=Counter(recent_payloads)[accepted_payload],
                    frame_path=frame_path,
                    scan_status=scan_status,
                    anpr_plate_number=args.anpr_plate_number,
                )
                record = mining_store.save_event(event)
                if can_log:
                    print(f"\nDetected with {method}:")
                    print(format_payload(accepted_payload))
                    print(f"Saved mining movement event: {record['record_file']}")
                    print(f"Direction: {record['direction']}")
                    print(f"Event status: {record['scan_status']}")
                    print(f"ANPR status: {record['anpr_match_status']}")
                    print(f"Total mining events saved: {record['event_number']}")
                    print(readiness)
                    saved_this_session += 1

                    if args.max_scans is not None and saved_this_session >= args.max_scans:
                        print(f"Reached --max-scans={args.max_scans}. Closing scanner.")
                        break
                else:
                    print(f"Duplicate suppressed for checkpoint {args.checkpoint_id}: {record['vehicle_id']}")

                if points is not None:
                    scanner.draw_detection(frame, points, method)

            if preview_enabled:
                if not show_preview("Mining Vehicle QR Scanner", frame, args.preview_scale):
                    preview_enabled = False
                    print(
                        "OpenCV preview is unavailable in this environment. "
                        "Continuing in terminal-only mode; press Ctrl+C to stop."
                    )

            if preview_enabled and cv2.waitKey(1) & 0xFF == ord("q"):
                break
    except KeyboardInterrupt:
        print("\nScanner stopped by user.")
    finally:
        cap.release()
        if preview_enabled:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
