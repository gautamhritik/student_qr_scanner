from __future__ import annotations

import json
from datetime import datetime

from mining_qr_scanner.shift_reports import export_shift_report, shift_label, summarize_shifts
from mining_qr_scanner.trips import reconstruct_trips


def event(**overrides) -> dict:
    data = {
        "event_id": "evt-in",
        "scanned_at": "2026-07-10T09:00:00+05:30",
        "date": "2026-07-10",
        "time": "09:00:00",
        "scan_status": "accepted",
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
        "load_status": "loaded",
        "load_weight_tons": "34.5",
        "route_id": "route-pit-a-crusher-1",
        "source_zone": "pit-a",
        "destination_zone": "crusher-1",
    }
    data.update(overrides)
    return data


def test_shift_label_handles_day_night_and_after_midnight_rollover() -> None:
    assert shift_label(datetime.fromisoformat("2026-07-10T09:00:00+05:30")) == {
        "shift_date": "2026-07-10",
        "shift_name": "day",
        "shift_key": "2026-07-10-day",
    }
    assert shift_label(datetime.fromisoformat("2026-07-10T20:00:00+05:30"))["shift_key"] == "2026-07-10-night"
    assert shift_label(datetime.fromisoformat("2026-07-11T02:00:00+05:30"))["shift_key"] == "2026-07-10-night"


def test_summarize_shifts_groups_events_trips_and_tonnage() -> None:
    events = [
        event(event_id="day-in"),
        event(event_id="day-out", direction="out", scanned_at="2026-07-10T09:45:00+05:30"),
        event(
            event_id="night-in",
            vehicle_id="TRUCK-002",
            material_type="coal",
            load_weight_tons="28",
            route_id="route-pit-b-stockyard-2",
            scanned_at="2026-07-10T20:00:00+05:30",
        ),
    ]

    summary = summarize_shifts(events, reconstruct_trips(events))
    rows = {row["shift_key"]: row for row in summary["shifts"]}

    assert summary["total_shifts"] == 2
    assert rows["2026-07-10-day"]["event_count"] == 2
    assert rows["2026-07-10-day"]["completed_trips"] == 1
    assert rows["2026-07-10-day"]["total_completed_tonnage"] == 34.5
    assert rows["2026-07-10-night"]["event_count"] == 1
    assert rows["2026-07-10-night"]["open_trips"] == 1
    assert rows["2026-07-10-night"]["top_material"] == "coal"


def test_export_shift_report_writes_csv_json_and_html(tmp_path) -> None:
    db = tmp_path / "mining_database"
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

    outputs = export_shift_report(db, tmp_path / "exports")

    assert outputs["csv"].name == "mining_shift_report.csv"
    assert outputs["json"].name == "mining_shift_summary.json"
    assert outputs["html"].name == "mining_shift_report.html"
    summary = json.loads(outputs["json"].read_text(encoding="utf-8"))
    assert summary["totals"]["completed_trips"] == 1
    assert "Mining Shift Report" in outputs["html"].read_text(encoding="utf-8")
