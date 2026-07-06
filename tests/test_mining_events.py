from __future__ import annotations

import json
from datetime import datetime, timezone

from student_qr_scanner.mining_events import MiningEventStore, build_scan_event, parse_vehicle_payload


def payload(**overrides) -> str:
    data = {
        "vehicle_id": "TRUCK-001",
        "plate_number": "mh12mn4101",
        "vehicle_type": "haul_truck",
        "site": "north-pit",
    }
    data.update(overrides)
    return json.dumps(data)


def test_parse_vehicle_payload_validates_required_fields() -> None:
    data, errors = parse_vehicle_payload(payload(vehicle_id=""))

    assert data["plate_number"] == "MH12MN4101"
    assert errors == ["missing vehicle_id"]


def test_build_scan_event_adds_gate_metadata_and_anpr_status() -> None:
    event = build_scan_event(
        payload(),
        "full-frame",
        datetime(2026, 7, 6, 9, 30, tzinfo=timezone.utc),
        camera_id="cam-1",
        checkpoint_id="gate-1",
        readiness="QR size in frame looks good.",
        anpr_plate_number="MH12MN4101",
    )

    assert event["vehicle_id"] == "TRUCK-001"
    assert event["camera_id"] == "cam-1"
    assert event["checkpoint_id"] == "gate-1"
    assert event["scan_status"] == "accepted"
    assert event["anpr_match_status"] == "match"


def test_mining_event_store_writes_history_and_record_file(tmp_path) -> None:
    store = MiningEventStore(tmp_path / "db")
    event = build_scan_event(
        payload(),
        "full-frame",
        datetime(2026, 7, 6, 9, 30, tzinfo=timezone.utc),
        camera_id="cam-1",
        checkpoint_id="gate-1",
    )

    saved = store.save_event(event)

    assert saved["event_number"] == 1
    assert store.load_events()[0]["vehicle_id"] == "TRUCK-001"
    assert (tmp_path / "db" / "records").exists()
