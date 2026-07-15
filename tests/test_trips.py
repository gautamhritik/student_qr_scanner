from __future__ import annotations

import json

from mining_qr_scanner.trips import (
    export_trips,
    filter_trips,
    reconstruct_trips,
    summarize_trips,
)


def event(**overrides) -> dict:
    data = {
        "event_id": "evt-in",
        "scanned_at": "2026-07-10T09:00:00+05:30",
        "scan_status": "accepted",
        "direction": "in",
        "vehicle_id": "TRUCK-001",
        "plate_number": "MH12MN4101",
        "driver_id": "DRV-001",
        "driver_name": "Ramesh Yadav",
        "material_type": "iron_ore",
        "load_status": "loaded",
        "load_weight_tons": "34.5",
        "route_id": "route-pit-a-crusher-1",
        "source_zone": "pit-a",
        "destination_zone": "crusher-1",
        "gate_id": "main-gate",
        "checkpoint_id": "gate-1",
    }
    data.update(overrides)
    return data


def test_reconstruct_trips_pairs_in_and_out_events() -> None:
    trips = reconstruct_trips(
        [
            event(event_id="in-1"),
            event(event_id="out-1", direction="out", scanned_at="2026-07-10T09:45:00+05:30"),
        ]
    )

    assert len(trips) == 1
    assert trips[0]["trip_status"] == "completed"
    assert trips[0]["duration_minutes"] == 45.0
    assert trips[0]["load_weight_tons"] == "34.5"


def test_reconstruct_trips_flags_open_missing_and_orphan_trips() -> None:
    trips = reconstruct_trips(
        [
            event(event_id="orphan-out", vehicle_id="TRUCK-002", direction="out"),
            event(event_id="in-1"),
            event(event_id="in-2", scanned_at="2026-07-10T10:00:00+05:30"),
        ]
    )

    statuses = [trip["trip_status"] for trip in trips]
    assert statuses == ["orphan_out", "missing_out", "open"]


def test_filter_and_summarize_trips() -> None:
    trips = reconstruct_trips(
        [
            event(event_id="in-1"),
            event(event_id="out-1", direction="out", scanned_at="2026-07-10T09:30:00+05:30"),
            event(
                event_id="coal-in",
                vehicle_id="TRUCK-002",
                material_type="coal",
                route_id="route-pit-b-stockyard-2",
                scanned_at="2026-07-10T10:00:00+05:30",
            ),
        ]
    )

    filtered = filter_trips(trips, material_type="iron_ore", trip_status="completed")
    summary = summarize_trips(trips)

    assert len(filtered) == 1
    assert summary["completed_trips"] == 1
    assert summary["open_trips"] == 1
    assert summary["total_completed_tonnage"] == 34.5
    assert summary["tonnage_by_material"]["iron_ore"] == 34.5


def test_summarize_trips_ignores_invalid_duration_values() -> None:
    trips = reconstruct_trips(
        [
            event(event_id="in-1"),
            event(event_id="out-1", direction="out", scanned_at="2026-07-10T09:30:00+05:30"),
        ]
    )
    trips[0]["duration_minutes"] = "not-a-number"

    summary = summarize_trips(trips)

    assert summary["completed_trips"] == 1
    assert summary["average_duration_minutes"] == 0


def test_export_trips_writes_csv_json_and_html(tmp_path) -> None:
    db = tmp_path / "db"
    db.mkdir()
    (db / "events.json").write_text(
        json.dumps(
            [
                event(event_id="in-1"),
                event(event_id="out-1", direction="out", scanned_at="2026-07-10T09:30:00+05:30"),
            ]
        ),
        encoding="utf-8",
    )

    outputs = export_trips(db, tmp_path / "exports")

    assert outputs["csv"].name == "mining_trips.csv"
    assert outputs["summary"].name == "mining_trips_summary.json"
    assert outputs["html"].name == "mining_trips_report.html"
    summary = json.loads(outputs["summary"].read_text(encoding="utf-8"))
    assert summary["completed_trips"] == 1
