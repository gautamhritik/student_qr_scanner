from __future__ import annotations

from collections import Counter
import csv
from datetime import datetime, timedelta
from html import escape
import json
from pathlib import Path
from typing import Iterable

from mining_qr_scanner.mining_events import MiningEventStore
from mining_qr_scanner.mining_reports import filter_events, flatten_event
from mining_qr_scanner.trips import filter_trips, numeric_tons, parse_time, reconstruct_trips


SHIFT_FIELDS = [
    "shift_key",
    "shift_date",
    "shift_name",
    "event_count",
    "accepted_events",
    "in_count",
    "out_count",
    "unique_vehicles",
    "completed_trips",
    "open_trips",
    "total_completed_tonnage",
    "average_trip_minutes",
    "top_gate",
    "top_material",
    "top_route",
]


def validate_shift_hours(day_start_hour: int, night_start_hour: int) -> None:
    if not 0 <= day_start_hour <= 23:
        raise ValueError("day_start_hour must be between 0 and 23.")
    if not 0 <= night_start_hour <= 23:
        raise ValueError("night_start_hour must be between 0 and 23.")
    if day_start_hour == night_start_hour:
        raise ValueError("day_start_hour and night_start_hour must be different.")


def shift_label(
    timestamp: datetime,
    *,
    day_start_hour: int = 6,
    night_start_hour: int = 18,
) -> dict:
    validate_shift_hours(day_start_hour, night_start_hour)
    hour = timestamp.hour
    if day_start_hour < night_start_hour:
        if day_start_hour <= hour < night_start_hour:
            shift_date = timestamp.date()
            shift_name = "day"
        else:
            shift_date = (timestamp - timedelta(days=1)).date() if hour < day_start_hour else timestamp.date()
            shift_name = "night"
    else:
        if night_start_hour <= hour < day_start_hour:
            shift_date = timestamp.date()
            shift_name = "night"
        else:
            shift_date = (timestamp - timedelta(days=1)).date() if hour < night_start_hour else timestamp.date()
            shift_name = "day"
    shift_date_text = shift_date.isoformat()
    return {
        "shift_date": shift_date_text,
        "shift_name": shift_name,
        "shift_key": f"{shift_date_text}-{shift_name}",
    }


def item_shift_key(
    item: dict,
    *,
    timestamp_fields: tuple[str, ...],
    day_start_hour: int,
    night_start_hour: int,
) -> str:
    for field in timestamp_fields:
        parsed = parse_time(item.get(field, ""))
        if parsed:
            return shift_label(
                parsed,
                day_start_hour=day_start_hour,
                night_start_hour=night_start_hour,
            )["shift_key"]
    return "unknown-unknown"


def most_common_label(counter: Counter) -> str:
    if not counter:
        return ""
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0][0]


def safe_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def shift_sort_key(shift_key: str) -> tuple[str, int]:
    shift_date, shift_name = shift_key.rsplit("-", 1)
    return (shift_date, 0 if shift_name == "day" else 1)


def summarize_shifts(
    events: Iterable[dict],
    trips: Iterable[dict],
    *,
    day_start_hour: int = 6,
    night_start_hour: int = 18,
) -> dict:
    validate_shift_hours(day_start_hour, night_start_hour)
    buckets: dict[str, dict] = {}

    def bucket_for_key(shift_key: str) -> dict:
        if shift_key not in buckets:
            shift_date, shift_name = shift_key.rsplit("-", 1)
            buckets[shift_key] = {
                "shift_key": shift_key,
                "shift_date": shift_date,
                "shift_name": shift_name,
                "events": [],
                "trips": [],
            }
        return buckets[shift_key]

    for event in events:
        flat = flatten_event(event)
        key = item_shift_key(
            flat,
            timestamp_fields=("scanned_at",),
            day_start_hour=day_start_hour,
            night_start_hour=night_start_hour,
        )
        bucket_for_key(key)["events"].append(flat)

    for trip in trips:
        key = item_shift_key(
            trip,
            timestamp_fields=("in_time", "out_time"),
            day_start_hour=day_start_hour,
            night_start_hour=night_start_hour,
        )
        bucket_for_key(key)["trips"].append(trip)

    rows = []
    totals = {
        "event_count": 0,
        "accepted_events": 0,
        "in_count": 0,
        "out_count": 0,
        "completed_trips": 0,
        "open_trips": 0,
        "total_completed_tonnage": 0.0,
    }
    for key in sorted(buckets, key=shift_sort_key):
        bucket = buckets[key]
        event_rows = bucket["events"]
        trip_rows = bucket["trips"]
        completed = [trip for trip in trip_rows if trip.get("trip_status") == "completed"]
        durations = [
            duration
            for trip in completed
            if (duration := safe_float(trip.get("duration_minutes"))) is not None
        ]
        tonnage = round(sum(numeric_tons(trip.get("load_weight_tons")) for trip in completed), 2)
        row = {
            "shift_key": bucket["shift_key"],
            "shift_date": bucket["shift_date"],
            "shift_name": bucket["shift_name"],
            "event_count": len(event_rows),
            "accepted_events": sum(1 for event in event_rows if event["scan_status"] == "accepted"),
            "in_count": sum(1 for event in event_rows if event["direction"] == "in"),
            "out_count": sum(1 for event in event_rows if event["direction"] == "out"),
            "unique_vehicles": len({event["vehicle_id"] for event in event_rows if event["vehicle_id"]}),
            "completed_trips": len(completed),
            "open_trips": sum(1 for trip in trip_rows if trip.get("trip_status") == "open"),
            "total_completed_tonnage": tonnage,
            "average_trip_minutes": round(sum(durations) / len(durations), 2) if durations else 0,
            "top_gate": most_common_label(Counter(event["gate_id"] for event in event_rows if event["gate_id"])),
            "top_material": most_common_label(
                Counter(trip["material_type"] for trip in trip_rows if trip.get("material_type"))
            ),
            "top_route": most_common_label(Counter(trip["route_id"] for trip in trip_rows if trip.get("route_id"))),
        }
        rows.append(row)
        for field in totals:
            totals[field] += row[field]

    totals["total_completed_tonnage"] = round(totals["total_completed_tonnage"], 2)
    return {
        "shift_settings": {
            "day_start_hour": day_start_hour,
            "night_start_hour": night_start_hour,
        },
        "total_shifts": len(rows),
        "totals": totals,
        "shifts": rows,
    }


def write_shift_csv(summary: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=SHIFT_FIELDS)
        writer.writeheader()
        for row in summary["shifts"]:
            writer.writerow({field: row.get(field, "") for field in SHIFT_FIELDS})
    return output_path


def write_shift_json(summary: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def write_shift_html(summary: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    totals = summary["totals"]
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(row.get('shift_key', '')))}</td>"
        f"<td>{escape(str(row.get('event_count', '')))}</td>"
        f"<td>{escape(str(row.get('in_count', '')))}</td>"
        f"<td>{escape(str(row.get('out_count', '')))}</td>"
        f"<td>{escape(str(row.get('completed_trips', '')))}</td>"
        f"<td>{escape(str(row.get('total_completed_tonnage', '')))}</td>"
        f"<td>{escape(str(row.get('average_trip_minutes', '')))}</td>"
        f"<td>{escape(str(row.get('top_gate', '')))}</td>"
        f"<td>{escape(str(row.get('top_material', '')))}</td>"
        f"<td>{escape(str(row.get('top_route', '')))}</td>"
        "</tr>"
        for row in summary["shifts"]
    )
    if not rows:
        rows = "<tr><td colspan=\"10\">No shift activity found</td></tr>"

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mining Shift Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2937; }}
    .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 20px 0; }}
    .metric {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 12px; }}
    .metric span {{ display: block; color: #6b7280; font-size: 13px; }}
    .metric strong {{ display: block; font-size: 24px; margin-top: 4px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; }}
    th {{ background: #f3f4f6; }}
  </style>
</head>
<body>
  <h1>Mining Shift Report</h1>
  <div class="metrics">
    <div class="metric"><span>Shifts</span><strong>{escape(str(summary["total_shifts"]))}</strong></div>
    <div class="metric"><span>Events</span><strong>{escape(str(totals["event_count"]))}</strong></div>
    <div class="metric"><span>Accepted reads</span><strong>{escape(str(totals["accepted_events"]))}</strong></div>
    <div class="metric"><span>Completed trips</span><strong>{escape(str(totals["completed_trips"]))}</strong></div>
    <div class="metric"><span>Open trips</span><strong>{escape(str(totals["open_trips"]))}</strong></div>
    <div class="metric"><span>Tonnage</span><strong>{escape(str(totals["total_completed_tonnage"]))}</strong></div>
  </div>
  <table>
    <thead><tr><th>Shift</th><th>Events</th><th>In</th><th>Out</th><th>Trips</th><th>Tons</th><th>Avg min</th><th>Top gate</th><th>Top material</th><th>Top route</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
    return output_path


def export_shift_report(
    database_dir: Path,
    output_dir: Path,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    day_start_hour: int = 6,
    night_start_hour: int = 18,
) -> dict[str, Path]:
    store = MiningEventStore(database_dir)
    all_events = store.load_events()
    events = filter_events(all_events, date_from=date_from, date_to=date_to)
    trips = filter_trips(
        reconstruct_trips(all_events),
        date_from=date_from,
        date_to=date_to,
    )
    summary = summarize_shifts(
        events,
        trips,
        day_start_hour=day_start_hour,
        night_start_hour=night_start_hour,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "csv": write_shift_csv(summary, output_dir / "mining_shift_report.csv"),
        "json": write_shift_json(summary, output_dir / "mining_shift_summary.json"),
        "html": write_shift_html(summary, output_dir / "mining_shift_report.html"),
    }
