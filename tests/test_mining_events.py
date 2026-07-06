from __future__ import annotations

import json
from datetime import datetime, timezone

from mining_qr_scanner.mining_events import MiningEventStore, build_scan_event, parse_vehicle_payload


def payload(**overrides) -> str:
    data = {
        "vehicle_id": "TRUCK-001",
        "plate_number": "mh12mn4101",
        "vehicle_type": "dump_truck",
        "driver_id": "DRV-001",
        "driver_name": "Ramesh Yadav",
        "license_number": "MH-DRV-4101",
        "material_type": "iron_ore",
        "load_status": "loaded",
        "load_weight_tons": "34.5",
        "source_zone": "pit-a",
        "destination_zone": "crusher-1",
        "route_id": "route-pit-a-crusher-1",
    }
    data.update(overrides)
    return json.dumps(data)


def build_event(direction="in", status=None) -> dict:
    return build_scan_event(
        payload(),
        "full-frame",
        datetime(2026, 7, 6, 9, 30, tzinfo=timezone.utc),
        site_id="mine-1",
        gate_id="main-gate",
        camera_id="pole-cam-1",
        checkpoint_id="gate-1",
        direction=direction,
        vote_window=5,
        min_votes=3,
        vote_count=3,
        scan_status=status,
        anpr_plate_number="MH12MN4101",
    )


def test_parse_vehicle_payload_validates_required_driver_and_cargo_fields() -> None:
    data, errors = parse_vehicle_payload(payload(driver_id=""))

    assert data["plate_number"] == "MH12MN4101"
    assert "missing driver_id" in errors


def test_build_scan_event_adds_gate_direction_voting_and_anpr_status() -> None:
    event = build_event()

    assert event["vehicle_id"] == "TRUCK-001"
    assert event["site_id"] == "mine-1"
    assert event["gate_id"] == "main-gate"
    assert event["direction"] == "in"
    assert event["vote_window"] == 5
    assert event["min_votes"] == 3
    assert event["vote_count"] == 3
    assert event["scan_status"] == "accepted"
    assert event["anpr_match_status"] == "match"


def test_mining_event_store_writes_events_and_updates_inside_outside_state(tmp_path) -> None:
    store = MiningEventStore(tmp_path / "mining_database")

    inside = store.save_event(build_event("in"))
    assert inside["event_number"] == 1
    assert store.load_vehicle_state()["TRUCK-001"]["current_status"] == "inside"

    store.save_event(build_event("out"))
    assert store.load_events()[1]["direction"] == "out"
    assert store.load_vehicle_state()["TRUCK-001"]["current_status"] == "outside"
    assert (tmp_path / "mining_database" / "events.json").exists()
    assert (tmp_path / "mining_database" / "vehicle_state.json").exists()


def test_duplicate_suppressed_event_does_not_update_vehicle_state(tmp_path) -> None:
    store = MiningEventStore(tmp_path / "mining_database")

    store.save_event(build_event("in"))
    store.save_event(build_event("out", status="duplicate_suppressed"))

    assert store.load_vehicle_state()["TRUCK-001"]["current_status"] == "inside"
    assert store.load_events()[1]["scan_status"] == "duplicate_suppressed"
