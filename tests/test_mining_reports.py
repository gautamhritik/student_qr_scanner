from __future__ import annotations

from student_qr_scanner.mining_reports import export_mining_events, filter_events, flatten_event, summarize_events


def event(**overrides) -> dict:
    data = {
        "event_number": 1,
        "event_id": "abc",
        "scanned_at": "2026-07-06T09:30:00+00:00",
        "date": "2026-07-06",
        "time": "09:30:00",
        "camera_id": "cam-1",
        "checkpoint_id": "gate-1",
        "vehicle_id": "TRUCK-001",
        "plate_number": "MH12MN4101",
        "vehicle_type": "haul_truck",
        "scan_status": "accepted",
        "anpr_match_status": "not_available",
    }
    data.update(overrides)
    return data


def test_flatten_and_summarize_mining_events() -> None:
    events = [event(), event(vehicle_id="EXC-014", checkpoint_id="pit-entry")]

    flat = flatten_event(events[0])
    summary = summarize_events(events)

    assert flat["vehicle_id"] == "TRUCK-001"
    assert summary["total_events"] == 2
    assert summary["by_checkpoint"]["gate-1"] == 1


def test_filter_events_by_vehicle_checkpoint_and_date() -> None:
    events = [event(), event(vehicle_id="EXC-014", checkpoint_id="pit-entry", date="2026-07-07")]

    filtered = filter_events(events, date_to="2026-07-06", vehicle_id="truck", checkpoint_id="gate-1")

    assert filtered == [events[0]]


def test_export_mining_events_writes_files(tmp_path) -> None:
    db = tmp_path / "db"
    db.mkdir()
    (db / "scan_events.json").write_text(
        "[{\"event_number\":1,\"event_id\":\"abc\",\"scanned_at\":\"2026-07-06T09:30:00+00:00\",\"date\":\"2026-07-06\",\"time\":\"09:30:00\",\"camera_id\":\"cam-1\",\"checkpoint_id\":\"gate-1\",\"vehicle_id\":\"TRUCK-001\",\"scan_status\":\"accepted\",\"anpr_match_status\":\"not_available\"}]",
        encoding="utf-8",
    )

    outputs = export_mining_events(db, tmp_path / "exports")

    assert outputs["csv"].exists()
    assert outputs["summary"].exists()
    assert outputs["html"].exists()
