from __future__ import annotations

import csv
from datetime import datetime, timedelta
from html import escape
import json
from pathlib import Path
from typing import Iterable


AUDIT_FIELDS = [
    "severity",
    "issue_type",
    "vehicle_id",
    "event_id",
    "scanned_at",
    "gate_id",
    "checkpoint_id",
    "direction",
    "message",
]


def parse_event_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def audit_events(
    events: Iterable[dict],
    vehicle_state: dict,
    *,
    now: datetime | None = None,
    stale_inside_hours: float = 12.0,
) -> dict:
    event_list = sorted(
        list(events),
        key=lambda event: event.get("scanned_at", ""),
    )
    issues = []
    last_accepted_by_vehicle: dict[str, dict] = {}
    now = now or datetime.now().astimezone()
    stale_delta = timedelta(hours=stale_inside_hours)

    for event in event_list:
        status = event.get("scan_status", "")
        vehicle_id = event.get("vehicle_id", "")

        if status == "validation_failed":
            issues.append(issue("high", "validation_failed", event, "QR payload failed validation."))
            continue
        if status == "duplicate_suppressed":
            issues.append(issue("low", "duplicate_suppressed", event, "Duplicate scan was suppressed by cooldown."))
            continue
        if status != "accepted" or not vehicle_id:
            continue

        previous = last_accepted_by_vehicle.get(vehicle_id)
        direction = event.get("direction", "")
        if previous:
            previous_direction = previous.get("direction", "")
            if previous_direction == direction:
                issues.append(
                    issue(
                        "medium",
                        "repeated_direction",
                        event,
                        f"Vehicle has repeated accepted {direction!r} movement without opposite direction.",
                    )
                )
        elif direction == "out":
            issues.append(
                issue(
                    "medium",
                    "out_without_prior_in",
                    event,
                    "Vehicle scanned out before any accepted in movement in this event history.",
                )
            )
        last_accepted_by_vehicle[vehicle_id] = event

    for state in vehicle_state.values():
        if state.get("current_status") != "inside":
            continue
        last_scan = parse_event_time(state.get("last_scan_at", ""))
        if last_scan is None:
            continue
        if last_scan.tzinfo is None and now.tzinfo is not None:
            last_scan = last_scan.replace(tzinfo=now.tzinfo)
        if now - last_scan > stale_delta:
            issues.append(
                {
                    "severity": "medium",
                    "issue_type": "stale_inside_vehicle",
                    "vehicle_id": state.get("vehicle_id", ""),
                    "event_id": "",
                    "scanned_at": state.get("last_scan_at", ""),
                    "gate_id": state.get("last_gate_id", ""),
                    "checkpoint_id": state.get("last_checkpoint_id", ""),
                    "direction": state.get("last_direction", ""),
                    "message": f"Vehicle has been inside for more than {stale_inside_hours:g} hours.",
                }
            )

    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    for row in issues:
        by_type[row["issue_type"]] = by_type.get(row["issue_type"], 0) + 1
        by_severity[row["severity"]] = by_severity.get(row["severity"], 0) + 1

    return {
        "total_events": len(event_list),
        "total_issues": len(issues),
        "by_issue_type": dict(sorted(by_type.items())),
        "by_severity": dict(sorted(by_severity.items())),
        "issues": issues,
    }


def issue(severity: str, issue_type: str, event: dict, message: str) -> dict:
    return {
        "severity": severity,
        "issue_type": issue_type,
        "vehicle_id": event.get("vehicle_id", ""),
        "event_id": event.get("event_id", ""),
        "scanned_at": event.get("scanned_at", ""),
        "gate_id": event.get("gate_id", ""),
        "checkpoint_id": event.get("checkpoint_id", ""),
        "direction": event.get("direction", ""),
        "message": message,
    }


def write_audit_json(report: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def write_audit_csv(report: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=AUDIT_FIELDS)
        writer.writeheader()
        writer.writerows(report["issues"])
    return output_path


def write_audit_html(report: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(row.get('severity', '')))}</td>"
        f"<td>{escape(str(row.get('issue_type', '')))}</td>"
        f"<td>{escape(str(row.get('vehicle_id', '')))}</td>"
        f"<td>{escape(str(row.get('scanned_at', '')))}</td>"
        f"<td>{escape(str(row.get('gate_id', '')))}</td>"
        f"<td>{escape(str(row.get('direction', '')))}</td>"
        f"<td>{escape(str(row.get('message', '')))}</td>"
        "</tr>"
        for row in report["issues"]
    )
    if not rows:
        rows = "<tr><td colspan=\"7\">No audit issues found</td></tr>"

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mining Movement Audit</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2937; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; }}
    th {{ background: #f3f4f6; }}
  </style>
</head>
<body>
  <h1>Mining Movement Audit</h1>
  <p>Total events: {report['total_events']} | Issues: {report['total_issues']}</p>
  <table>
    <thead><tr><th>Severity</th><th>Type</th><th>Vehicle</th><th>Scanned at</th><th>Gate</th><th>Direction</th><th>Message</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
    return output_path
