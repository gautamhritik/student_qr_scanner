from __future__ import annotations

from datetime import datetime
from pathlib import Path

import cv2

from mining_qr_scanner.mining_events import MiningEventStore, build_scan_event
from mining_qr_scanner.scanner import LightingAdaptiveQRScanner

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def collect_image_paths(inputs: list[Path]) -> list[Path]:
    paths: list[Path] = []
    for item in inputs:
        if item.is_dir():
            paths.extend(
                path
                for path in sorted(item.rglob("*"))
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
            )
        elif item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS:
            paths.append(item)
    return paths


def scan_image_paths(
    image_paths: list[Path],
    store: MiningEventStore,
    *,
    site_id: str,
    gate_id: str,
    checkpoint_id: str,
    camera_id: str,
    direction: str,
    scanner: LightingAdaptiveQRScanner | None = None,
    save_failures: bool = False,
    anpr_plate_number: str | None = None,
) -> list[dict]:
    scanner = scanner or LightingAdaptiveQRScanner()
    records = []
    for image_path in image_paths:
        frame = cv2.imread(str(image_path))
        now = datetime.now().astimezone()
        if frame is None:
            if not save_failures:
                continue
            event = build_scan_event(
                "",
                "image-read-failed",
                now,
                site_id=site_id,
                gate_id=gate_id,
                camera_id=camera_id,
                checkpoint_id=checkpoint_id,
                direction=direction,
                frame_path=str(image_path),
                scan_status="image_read_failed",
                anpr_plate_number=anpr_plate_number,
            )
            records.append(store.save_event(event))
            continue

        result = scanner.detect(frame)
        if result:
            payload, points, method = result
            readiness = scanner.estimate_distance_readiness(points, frame)
            event = build_scan_event(
                payload,
                method,
                now,
                site_id=site_id,
                gate_id=gate_id,
                camera_id=camera_id,
                checkpoint_id=checkpoint_id,
                direction=direction,
                readiness=readiness,
                frame_path=str(image_path),
                anpr_plate_number=anpr_plate_number,
            )
            records.append(store.save_event(event))
        elif save_failures:
            event = build_scan_event(
                "",
                "no-qr-detected",
                now,
                site_id=site_id,
                gate_id=gate_id,
                camera_id=camera_id,
                checkpoint_id=checkpoint_id,
                direction=direction,
                frame_path=str(image_path),
                scan_status="no_qr_detected",
                anpr_plate_number=anpr_plate_number,
            )
            records.append(store.save_event(event))
    return records
