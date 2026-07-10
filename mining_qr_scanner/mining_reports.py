from __future__ import annotations

from collections import Counter
import csv
from html import escape
import json
from pathlib import Path
from typing import Iterable

from mining_qr_scanner.mining_events import MiningEventStore


CSV_FIELDS = [
    "event_number",
    "event_id",
    "scanned_at",
    "date",
    "time",
    "site_id",
    "gate_id",
    "camera_id",
    "checkpoint_id",
    "direction",
    "vehicle_id",
    "plate_number",
    "vehicle_type",
    "owner_operator",
    "permit_id",
    "rfid_tag",
    "driver_id",
    "driver_name",
    "license_number",
    "contact_number",
    "company",
    "material_type",
    "load_status",
    "load_weight_tons",
    "source_zone",
    "destination_zone",
    "route_id",
    "payload_version",
    "payload_id",
    "issued_at",
    "expires_on",
    "checksum",
    "detection_method",
    "scan_status",
    "anpr_plate_number",
    "anpr_match_status",
    "readiness",
    "vote_window",
    "min_votes",
    "vote_count",
    "frame_path",
    "record_file",
]

VEHICLE_STATE_FIELDS = [
    "vehicle_id",
    "plate_number",
    "current_status",
    "last_scan_at",
    "last_direction",
    "last_site_id",
    "last_gate_id",
    "last_checkpoint_id",
    "last_camera_id",
    "driver_id",
    "driver_name",
    "material_type",
    "load_status",
    "load_weight_tons",
    "route_id",
    "source_zone",
    "destination_zone",
]


def flatten_event(event: dict) -> dict:
    flattened = {field: event.get(field, "") for field in CSV_FIELDS}
    return {field: flattened.get(field, "") for field in CSV_FIELDS}


def filter_events(
    events: Iterable[dict],
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    vehicle_id: str | None = None,
    plate_number: str | None = None,
    driver_id: str | None = None,
    material_type: str | None = None,
    gate_id: str | None = None,
    checkpoint_id: str | None = None,
    direction: str | None = None,
    scan_status: str | None = None,
) -> list[dict]:
    vehicle_query = vehicle_id.casefold() if vehicle_id else None
    plate_query = plate_number.casefold() if plate_number else None
    driver_query = driver_id.casefold() if driver_id else None
    material_query = material_type.casefold() if material_type else None
    gate_query = gate_id.casefold() if gate_id else None
    checkpoint_query = checkpoint_id.casefold() if checkpoint_id else None
    direction_query = direction.casefold() if direction else None
    status_query = scan_status.casefold() if scan_status else None
    filtered = []
    for event in events:
        flat = flatten_event(event)
        if date_from and flat["date"] < date_from:
            continue
        if date_to and flat["date"] > date_to:
            continue
        if vehicle_query and vehicle_query not in flat["vehicle_id"].casefold():
            continue
        if plate_query and plate_query not in flat["plate_number"].casefold():
            continue
        if driver_query and driver_query not in flat["driver_id"].casefold():
            continue
        if material_query and material_query != flat["material_type"].casefold():
            continue
        if gate_query and gate_query != flat["gate_id"].casefold():
            continue
        if checkpoint_query and checkpoint_query != flat["checkpoint_id"].casefold():
            continue
        if direction_query and direction_query != flat["direction"].casefold():
            continue
        if status_query and status_query != flat["scan_status"].casefold():
            continue
        filtered.append(event)
    return filtered


def summarize_events(events: Iterable[dict]) -> dict:
    event_list = [flatten_event(event) for event in events]
    scanned_at_values = sorted(event["scanned_at"] for event in event_list if event["scanned_at"])
    return {
        "total_events": len(event_list),
        "unique_vehicles": len({event["vehicle_id"] for event in event_list if event["vehicle_id"]}),
        "by_vehicle": dict(sorted(Counter(event["vehicle_id"] for event in event_list if event["vehicle_id"]).items())),
        "by_driver": dict(sorted(Counter(event["driver_id"] for event in event_list if event["driver_id"]).items())),
        "by_gate": dict(sorted(Counter(event["gate_id"] for event in event_list if event["gate_id"]).items())),
        "by_checkpoint": dict(sorted(Counter(event["checkpoint_id"] for event in event_list if event["checkpoint_id"]).items())),
        "by_camera": dict(sorted(Counter(event["camera_id"] for event in event_list if event["camera_id"]).items())),
        "by_direction": dict(sorted(Counter(event["direction"] for event in event_list if event["direction"]).items())),
        "by_route": dict(sorted(Counter(event["route_id"] for event in event_list if event["route_id"]).items())),
        "by_material": dict(sorted(Counter(event["material_type"] for event in event_list if event["material_type"]).items())),
        "by_date": dict(sorted(Counter(event["date"] for event in event_list if event["date"]).items())),
        "by_scan_status": dict(sorted(Counter(event["scan_status"] for event in event_list if event["scan_status"]).items())),
        "by_anpr_match_status": dict(sorted(Counter(event["anpr_match_status"] for event in event_list if event["anpr_match_status"]).items())),
        "first_event_at": scanned_at_values[0] if scanned_at_values else "",
        "last_event_at": scanned_at_values[-1] if scanned_at_values else "",
    }


def write_csv(events: Iterable[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for event in events:
            writer.writerow(flatten_event(event))
    return output_path


def write_summary(events: Iterable[dict], output_path: Path, vehicle_state: dict | None = None) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary = summarize_events(events)
    summary["vehicle_state"] = summarize_vehicle_state(vehicle_state or {})
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def vehicle_state_rows(vehicle_state: dict) -> list[dict]:
    rows = []
    for item in vehicle_state.values():
        rows.append({field: item.get(field, "") for field in VEHICLE_STATE_FIELDS})
    return sorted(rows, key=lambda row: (row["current_status"], row["vehicle_id"]))


def write_vehicle_state_csv(vehicle_state: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=VEHICLE_STATE_FIELDS)
        writer.writeheader()
        writer.writerows(vehicle_state_rows(vehicle_state))
    return output_path


def write_vehicle_state_json(vehicle_state: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "summary": summarize_vehicle_state(vehicle_state),
                "vehicles": vehicle_state_rows(vehicle_state),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return output_path


def summarize_vehicle_state(vehicle_state: dict) -> dict:
    values = list(vehicle_state.values())
    return {
        "total_tracked_vehicles": len(values),
        "inside": sum(1 for item in values if item.get("current_status") == "inside"),
        "outside": sum(1 for item in values if item.get("current_status") == "outside"),
        "unknown": sum(1 for item in values if item.get("current_status") == "unknown"),
    }


def write_html_report(events: Iterable[dict], output_path: Path, vehicle_state: dict | None = None) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    event_list = list(events)
    summary = summarize_events(event_list)
    state_summary = summarize_vehicle_state(vehicle_state or {})
    recent_events = sorted(
        [flatten_event(event) for event in event_list],
        key=lambda event: event["scanned_at"],
        reverse=True,
    )[:30]

    def metric(label: str, value) -> str:
        return (
            "<div class=\"metric\">"
            f"<span>{escape(label)}</span>"
            f"<strong>{escape(str(value))}</strong>"
            "</div>"
        )

    def count_rows(values: dict) -> str:
        if not values:
            return "<tr><td colspan=\"2\">No data</td></tr>"
        return "\n".join(
            f"<tr><td>{escape(str(label))}</td><td>{escape(str(count))}</td></tr>"
            for label, count in values.items()
        )

    event_rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(event['scanned_at']))}</td>"
        f"<td>{escape(str(event['checkpoint_id']))}</td>"
        f"<td>{escape(str(event['direction']))}</td>"
        f"<td>{escape(str(event['vehicle_id']))}</td>"
        f"<td>{escape(str(event['plate_number']))}</td>"
        f"<td>{escape(str(event['driver_name']))}</td>"
        f"<td>{escape(str(event['material_type']))}</td>"
        f"<td>{escape(str(event['scan_status']))}</td>"
        f"<td>{escape(str(event['anpr_match_status']))}</td>"
        "</tr>"
        for event in recent_events
    )
    if not event_rows:
        event_rows = "<tr><td colspan=\"9\">No mining scan events found</td></tr>"

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mining QR Scan Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2937; }}
    h1, h2 {{ margin-bottom: 8px; }}
    .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 20px 0; }}
    .metric {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 12px; }}
    .metric span {{ display: block; color: #6b7280; font-size: 13px; }}
    .metric strong {{ display: block; font-size: 24px; margin-top: 4px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0 28px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; }}
    th {{ background: #f3f4f6; }}
  </style>
</head>
<body>
  <h1>Mining QR Scan Report</h1>
  <div class="metrics">
    {metric("Total events", summary["total_events"])}
    {metric("Unique vehicles", summary["unique_vehicles"])}
    {metric("Vehicles inside", state_summary["inside"])}
    {metric("Vehicles outside", state_summary["outside"])}
    {metric("First event", summary["first_event_at"] or "N/A")}
    {metric("Last event", summary["last_event_at"] or "N/A")}
  </div>
  <h2>Events by gate</h2>
  <table><thead><tr><th>Gate</th><th>Events</th></tr></thead><tbody>{count_rows(summary["by_gate"])}</tbody></table>
  <h2>Events by material</h2>
  <table><thead><tr><th>Material</th><th>Events</th></tr></thead><tbody>{count_rows(summary["by_material"])}</tbody></table>
  <h2>Events by direction</h2>
  <table><thead><tr><th>Direction</th><th>Events</th></tr></thead><tbody>{count_rows(summary["by_direction"])}</tbody></table>
  <h2>Events by status</h2>
  <table><thead><tr><th>Status</th><th>Events</th></tr></thead><tbody>{count_rows(summary["by_scan_status"])}</tbody></table>
  <h2>Recent events</h2>
  <table>
    <thead><tr><th>Scanned at</th><th>Checkpoint</th><th>Direction</th><th>Vehicle</th><th>Plate</th><th>Driver</th><th>Material</th><th>Status</th><th>ANPR</th></tr></thead>
    <tbody>{event_rows}</tbody>
  </table>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
    return output_path


def export_mining_events(
    database_dir: Path,
    output_dir: Path,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    vehicle_id: str | None = None,
    plate_number: str | None = None,
    driver_id: str | None = None,
    material_type: str | None = None,
    gate_id: str | None = None,
    checkpoint_id: str | None = None,
    direction: str | None = None,
    scan_status: str | None = None,
) -> dict[str, Path]:
    store = MiningEventStore(database_dir)
    events = filter_events(
        store.load_events(),
        date_from=date_from,
        date_to=date_to,
        vehicle_id=vehicle_id,
        plate_number=plate_number,
        driver_id=driver_id,
        material_type=material_type,
        gate_id=gate_id,
        checkpoint_id=checkpoint_id,
        direction=direction,
        scan_status=scan_status,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    vehicle_state = store.load_vehicle_state()
    return {
        "csv": write_csv(events, output_dir / "mining_events.csv"),
        "summary": write_summary(events, output_dir / "mining_summary.json", vehicle_state),
        "html": write_html_report(events, output_dir / "mining_report.html", vehicle_state),
        "vehicle_state_csv": write_vehicle_state_csv(vehicle_state, output_dir / "vehicle_state.csv"),
        "vehicle_state_json": write_vehicle_state_json(vehicle_state, output_dir / "vehicle_state.json"),
    }
