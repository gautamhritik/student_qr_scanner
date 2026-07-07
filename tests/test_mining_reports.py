from __future__ import annotations

import json

from mining_qr_scanner.mining_reports import (
    export_mining_events,
    filter_events,
    flatten_event,
    summarize_events,
    vehicle_state_rows,
)


def event(**overrides) -> dict:
    data = {
        "event_number": 1,
        "event_id": "abc",
        "scanned_at": "2026-07-06T09:30:00+00:00",
        "date": "2026-07-06",
        "time": "09:30:00",
        "site_id": "mine-1",
        "gate_id": "main-gate",
        "camera_id": "pole-cam-1",
        "checkpoint_id": "gate-1",
        "direction": "in",
        "vehicle_id": "TRUCK-001",
        "plate_number": "MH12MN4101",
        "vehicle_type": "dump_truck",
        "driver_id": "DRV-001",
        "driver_name": "Ramesh Yadav",
        "material_type": "iron_ore",
        "route_id": "route-pit-a-crusher-1",
        "scan_status": "accepted",
        "anpr_match_status": "not_available",
    }
    data.update(overrides)
    return data


def test_flatten_and_summarize_mining_events() -> None:
    events = [
        event(),
        event(vehicle_id="TRUCK-002", driver_id="DRV-002", gate_id="west-gate", material_type="coal", direction="out"),
    ]

    flat = flatten_event(events[0])
    summary = summarize_events(events)

    assert flat["vehicle_id"] == "TRUCK-001"
    assert flat["driver_id"] == "DRV-001"
    assert summary["total_events"] == 2
    assert summary["by_gate"]["main-gate"] == 1
    assert summary["by_material"]["iron_ore"] == 1
    assert summary["by_direction"]["out"] == 1


def test_filter_events_by_vehicle_plate_driver_material_gate_direction_and_date() -> None:
    events = [
        event(),
        event(vehicle_id="TRUCK-002", plate_number="MH12MN4102", driver_id="DRV-002", material_type="coal", gate_id="west-gate", direction="out", date="2026-07-07"),
    ]

    filtered = filter_events(
        events,
        date_to="2026-07-06",
        vehicle_id="truck",
        plate_number="4101",
        driver_id="drv-001",
        material_type="iron_ore",
        gate_id="main-gate",
        direction="in",
    )

    assert filtered == [events[0]]


def test_export_mining_events_writes_files_and_state_summary(tmp_path) -> None:
    db = tmp_path / "mining_database"
    db.mkdir()
    (db / "events.json").write_text(json.dumps([event()]), encoding="utf-8")
    (db / "vehicle_state.json").write_text(
        json.dumps({"TRUCK-001": {"current_status": "inside"}}),
        encoding="utf-8",
    )

    outputs = export_mining_events(db, tmp_path / "exports")

    assert outputs["csv"].name == "mining_events.csv"
    assert outputs["summary"].name == "mining_summary.json"
    assert outputs["html"].name == "mining_report.html"
    assert outputs["vehicle_state_csv"].name == "vehicle_state.csv"
    assert outputs["vehicle_state_json"].name == "vehicle_state.json"
    summary = json.loads(outputs["summary"].read_text(encoding="utf-8"))
    assert summary["vehicle_state"]["inside"] == 1


def test_vehicle_state_rows_are_flattened_and_sorted() -> None:
    rows = vehicle_state_rows(
        {
            "TRUCK-002": {"vehicle_id": "TRUCK-002", "current_status": "outside"},
            "TRUCK-001": {"vehicle_id": "TRUCK-001", "current_status": "inside"},
        }
    )

    assert [row["vehicle_id"] for row in rows] == ["TRUCK-001", "TRUCK-002"]
