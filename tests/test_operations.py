from __future__ import annotations

import json

from mining_qr_scanner.operations import build_operations_summary, export_operations_summary


def event(**overrides) -> dict:
    data = {
        "event_id": "evt-in",
        "scanned_at": "2026-07-10T09:00:00+05:30",
        "date": "2026-07-10",
        "time": "09:00:00",
        "scan_status": "accepted",
        "site_id": "mine-1",
        "gate_id": "main-gate",
        "checkpoint_id": "gate-1",
        "camera_id": "pole-cam-1",
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


def write_database(db, events: list[dict], vehicle_state: dict | None = None) -> None:
    db.mkdir()
    (db / "events.json").write_text(json.dumps(events), encoding="utf-8")
    (db / "vehicle_state.json").write_text(json.dumps(vehicle_state or {}), encoding="utf-8")


def test_build_operations_summary_combines_events_state_trips_audit_and_environment(
    tmp_path,
    monkeypatch,
) -> None:
    db = tmp_path / "mining_database"
    write_database(
        db,
        [
            event(event_id="in-1"),
            event(event_id="out-1", direction="out", scanned_at="2026-07-10T09:45:00+05:30"),
        ],
        {"TRUCK-001": {"vehicle_id": "TRUCK-001", "current_status": "outside"}},
    )
    monkeypatch.setattr(
        "mining_qr_scanner.operations.environment_report",
        lambda: {
            "cv2_version": "test-version",
            "preview_supported": True,
            "gui_backend": "Win32 UI",
        },
    )

    summary = build_operations_summary(db)

    assert summary["events"]["total_events"] == 2
    assert summary["events"]["by_gate"]["main-gate"] == 2
    assert summary["vehicle_state"]["outside"] == 1
    assert summary["trips"]["completed_trips"] == 1
    assert summary["trips"]["total_completed_tonnage"] == 34.5
    assert summary["audit"]["total_issues"] == 0
    assert summary["opencv_environment"]["cv2_version"] == "test-version"


def test_export_operations_summary_writes_json_and_html_without_environment(tmp_path) -> None:
    db = tmp_path / "mining_database"
    write_database(db, [event()])

    outputs = export_operations_summary(
        db,
        tmp_path / "exports",
        include_environment=False,
    )

    assert outputs["json"].name == "operations_summary.json"
    assert outputs["html"].name == "operations_summary.html"
    summary = json.loads(outputs["json"].read_text(encoding="utf-8"))
    html = outputs["html"].read_text(encoding="utf-8")
    assert "opencv_environment" not in summary
    assert "Mining Operations Summary" in html
    assert "OpenCV Environment" not in html
    assert "TRUCK-001" not in html
