from __future__ import annotations

from collections import Counter
import csv
from html import escape
import json
from pathlib import Path
from typing import Iterable

from student_qr_scanner.mining_events import MiningEventStore


CSV_FIELDS = [
    "event_number",
    "event_id",
    "scanned_at",
    "date",
    "time",
    "camera_id",
    "checkpoint_id",
    "vehicle_id",
    "plate_number",
    "vehicle_type",
    "site",
    "assigned_route",
    "owner_operator",
    "detection_method",
    "scan_status",
    "anpr_plate_number",
    "anpr_match_status",
    "readiness",
    "record_file",
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
    checkpoint_id: str | None = None,
    scan_status: str | None = None,
) -> list[dict]:
    vehicle_query = vehicle_id.casefold() if vehicle_id else None
    checkpoint_query = checkpoint_id.casefold() if checkpoint_id else None
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
        if checkpoint_query and checkpoint_query != flat["checkpoint_id"].casefold():
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
        "by_checkpoint": dict(sorted(Counter(event["checkpoint_id"] for event in event_list if event["checkpoint_id"]).items())),
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


def write_summary(events: Iterable[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summarize_events(events), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def write_html_report(events: Iterable[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    event_list = list(events)
    summary = summarize_events(event_list)
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
        f"<td>{escape(str(event['vehicle_id']))}</td>"
        f"<td>{escape(str(event['plate_number']))}</td>"
        f"<td>{escape(str(event['scan_status']))}</td>"
        f"<td>{escape(str(event['anpr_match_status']))}</td>"
        "</tr>"
        for event in recent_events
    )
    if not event_rows:
        event_rows = "<tr><td colspan=\"6\">No mining scan events found</td></tr>"

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
    {metric("First event", summary["first_event_at"] or "N/A")}
    {metric("Last event", summary["last_event_at"] or "N/A")}
  </div>
  <h2>Events by checkpoint</h2>
  <table><thead><tr><th>Checkpoint</th><th>Events</th></tr></thead><tbody>{count_rows(summary["by_checkpoint"])}</tbody></table>
  <h2>Events by status</h2>
  <table><thead><tr><th>Status</th><th>Events</th></tr></thead><tbody>{count_rows(summary["by_scan_status"])}</tbody></table>
  <h2>Recent events</h2>
  <table>
    <thead><tr><th>Scanned at</th><th>Checkpoint</th><th>Vehicle</th><th>Plate</th><th>Status</th><th>ANPR</th></tr></thead>
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
    checkpoint_id: str | None = None,
    scan_status: str | None = None,
) -> dict[str, Path]:
    store = MiningEventStore(database_dir)
    events = filter_events(
        store.load_events(),
        date_from=date_from,
        date_to=date_to,
        vehicle_id=vehicle_id,
        checkpoint_id=checkpoint_id,
        scan_status=scan_status,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "csv": write_csv(events, output_dir / "mining_scan_events.csv"),
        "summary": write_summary(events, output_dir / "mining_scan_summary.json"),
        "html": write_html_report(events, output_dir / "mining_scan_report.html"),
    }
