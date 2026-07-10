from __future__ import annotations

import json
from datetime import datetime

import cv2
import numpy as np

from mining_qr_scanner.mining_events import MiningEventStore
from mining_qr_scanner.offline_scan import collect_image_paths, scan_image_paths
from mining_qr_scanner.payloads import build_qr_payload


def payload() -> str:
    return json.dumps(
        build_qr_payload(
            {
            "vehicle_id": "TRUCK-001",
            "plate_number": "MH12MN4101",
            "vehicle_type": "dump_truck",
            "driver_id": "DRV-001",
            "driver_name": "Ramesh Yadav",
            "license_number": "MH-DRV-4101",
            "material_type": "iron_ore",
            "load_status": "loaded",
            "source_zone": "pit-a",
            "destination_zone": "crusher-1",
            "route_id": "route-pit-a-crusher-1",
            },
            issued_at=datetime(2026, 7, 8).date(),
        )
    )


class FakeScanner:
    def detect(self, frame):
        return payload(), np.array([[[0, 0], [10, 0], [10, 10], [0, 10]]], dtype=np.float32), "fake-method"

    def estimate_distance_readiness(self, points, frame) -> str:
        return "fake readiness"


class NoQrScanner:
    def detect(self, frame):
        return None


def write_image(path) -> None:
    image = np.full((40, 40, 3), 255, dtype=np.uint8)
    cv2.imwrite(str(path), image)


def test_collect_image_paths_reads_files_and_folders(tmp_path) -> None:
    image_path = tmp_path / "frame.png"
    nested = tmp_path / "nested"
    nested.mkdir()
    nested_image = nested / "nested.jpg"
    write_image(image_path)
    write_image(nested_image)
    (tmp_path / "notes.txt").write_text("not an image", encoding="utf-8")

    paths = collect_image_paths([tmp_path])

    assert paths == [image_path, nested_image]


def test_scan_image_paths_stores_accepted_event_and_updates_state(tmp_path) -> None:
    image_path = tmp_path / "frame.png"
    write_image(image_path)
    store = MiningEventStore(tmp_path / "db")

    records = scan_image_paths(
        [image_path],
        store,
        site_id="mine-1",
        gate_id="main-gate",
        checkpoint_id="gate-1",
        camera_id="pole-cam-1",
        direction="in",
        scanner=FakeScanner(),
    )

    assert records[0]["vehicle_id"] == "TRUCK-001"
    assert records[0]["frame_path"] == str(image_path)
    assert store.load_vehicle_state()["TRUCK-001"]["current_status"] == "inside"


def test_scan_image_paths_can_store_no_qr_failures(tmp_path) -> None:
    image_path = tmp_path / "frame.png"
    write_image(image_path)
    store = MiningEventStore(tmp_path / "db")

    records = scan_image_paths(
        [image_path],
        store,
        site_id="mine-1",
        gate_id="main-gate",
        checkpoint_id="gate-1",
        camera_id="pole-cam-1",
        direction="in",
        scanner=NoQrScanner(),
        save_failures=True,
    )

    assert records[0]["scan_status"] == "no_qr_detected"
    assert store.load_vehicle_state() == {}
