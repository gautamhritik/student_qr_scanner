from __future__ import annotations

from datetime import datetime, timedelta, timezone

from mining_qr_scanner.audit import audit_events, write_audit_csv, write_audit_html, write_audit_json


def event(**overrides) -> dict:
    data = {
        "event_id": "evt-1",
        "scanned_at": "2026-07-08T10:00:00+05:30",
        "vehicle_id": "TRUCK-001",
        "gate_id": "main-gate",
        "checkpoint_id": "gate-1",
        "direction": "in",
        "scan_status": "accepted",
    }
    data.update(overrides)
    return data


def test_audit_events_flags_repeated_direction_out_without_in_and_suppressed() -> None:
    report = audit_events(
        [
            event(event_id="evt-out", vehicle_id="TRUCK-002", direction="out"),
            event(event_id="evt-in-1"),
            event(event_id="evt-in-2"),
            event(event_id="evt-dup", scan_status="duplicate_suppressed"),
            event(event_id="evt-invalid", scan_status="validation_failed"),
        ],
        {},
        now=datetime(2026, 7, 8, 11, 0, tzinfo=timezone.utc),
    )

    assert report["total_issues"] == 4
    assert report["by_issue_type"]["out_without_prior_in"] == 1
    assert report["by_issue_type"]["repeated_direction"] == 1
    assert report["by_issue_type"]["duplicate_suppressed"] == 1
    assert report["by_issue_type"]["validation_failed"] == 1


def test_audit_events_flags_stale_inside_vehicle() -> None:
    now = datetime.now(timezone.utc)
    report = audit_events(
        [],
        {
            "TRUCK-001": {
                "vehicle_id": "TRUCK-001",
                "current_status": "inside",
                "last_scan_at": (now - timedelta(hours=13)).isoformat(timespec="seconds"),
                "last_gate_id": "main-gate",
            }
        },
        now=now,
        stale_inside_hours=12,
    )

    assert report["issues"][0]["issue_type"] == "stale_inside_vehicle"


def test_write_audit_outputs(tmp_path) -> None:
    report = audit_events([event(scan_status="validation_failed")], {})

    assert write_audit_json(report, tmp_path / "audit.json").exists()
    assert write_audit_csv(report, tmp_path / "audit.csv").exists()
    assert write_audit_html(report, tmp_path / "audit.html").exists()
