from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import datetime
from html import escape
import json
from pathlib import Path
from typing import Iterable

from mining_qr_scanner.mining_events import MiningEventStore


TRIP_FIELDS = [
    "trip_id",
    "trip_status",
    "vehicle_id",
    "plate_number",
    "driver_id",
    "driver_name",
    "material_type",
    "load_status",
    "load_weight_tons",
    "route_id",
    "source_zone",
    "destination_zone",
    "in_event_id",
    "out_event_id",
    "in_time",
    "out_time",
    "duration_minutes",
    "in_gate_id",
    "out_gate_id",
    "in_checkpoint_id",
    "out_checkpoint_id",
]


def parse_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def numeric_tons(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def build_trip(in_event: dict | None, out_event: dict | None, status: str) -> dict:
    source = in_event or out_event or {}
    in_time = parse_time(in_event.get("scanned_at", "")) if in_event else None
    out_time = parse_time(out_event.get("scanned_at", "")) if out_event else None
    duration = ""
    if in_time and out_time:
        duration = round((out_time - in_time).total_seconds() / 60, 2)

    vehicle_id = source.get("vehicle_id", "")
    trip_id = "-".join(
        value
        for value in [
            "trip",
            vehicle_id.lower(),
            (in_event or {}).get("event_id", "")[:8],
            (out_event or {}).get("event_id", "")[:8],
        ]
        if value
    )
    return {
        "trip_id": trip_id,
        "trip_status": status,
        "vehicle_id": vehicle_id,
        "plate_number": source.get("plate_number", ""),
        "driver_id": source.get("driver_id", ""),
        "driver_name": source.get("driver_name", ""),
        "material_type": source.get("material_type", ""),
        "load_status": source.get("load_status", ""),
        "load_weight_tons": source.get("load_weight_tons", ""),
        "route_id": source.get("route_id", ""),
        "source_zone": source.get("source_zone", ""),
        "destination_zone": source.get("destination_zone", ""),
        "in_event_id": (in_event or {}).get("event_id", ""),
        "out_event_id": (out_event or {}).get("event_id", ""),
        "in_time": (in_event or {}).get("scanned_at", ""),
        "out_time": (out_event or {}).get("scanned_at", ""),
        "duration_minutes": duration,
        "in_gate_id": (in_event or {}).get("gate_id", ""),
        "out_gate_id": (out_event or {}).get("gate_id", ""),
        "in_checkpoint_id": (in_event or {}).get("checkpoint_id", ""),
        "out_checkpoint_id": (out_event or {}).get("checkpoint_id", ""),
    }


def reconstruct_trips(events: Iterable[dict]) -> list[dict]:
    accepted = sorted(
        [event for event in events if event.get("scan_status") == "accepted" and event.get("vehicle_id")],
        key=lambda event: event.get("scanned_at", ""),
    )
    open_by_vehicle: dict[str, dict] = {}
    trips = []

    for event in accepted:
        vehicle_id = event["vehicle_id"]
        direction = event.get("direction")
        if direction == "in":
            previous_open = open_by_vehicle.get(vehicle_id)
            if previous_open:
                trips.append(build_trip(previous_open, None, "missing_out"))
            open_by_vehicle[vehicle_id] = event
        elif direction == "out":
            in_event = open_by_vehicle.pop(vehicle_id, None)
            if in_event:
                trips.append(build_trip(in_event, event, "completed"))
            else:
                trips.append(build_trip(None, event, "orphan_out"))

    for in_event in open_by_vehicle.values():
        trips.append(build_trip(in_event, None, "open"))
    return trips


def filter_trips(
    trips: Iterable[dict],
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    vehicle_id: str | None = None,
    material_type: str | None = None,
    route_id: str | None = None,
    trip_status: str | None = None,
) -> list[dict]:
    vehicle_query = vehicle_id.casefold() if vehicle_id else None
    material_query = material_type.casefold() if material_type else None
    route_query = route_id.casefold() if route_id else None
    status_query = trip_status.casefold() if trip_status else None
    filtered = []
    for trip in trips:
        date_value = (trip.get("in_time") or trip.get("out_time") or "")[:10]
        if date_from and date_value < date_from:
            continue
        if date_to and date_value > date_to:
            continue
        if vehicle_query and vehicle_query not in trip.get("vehicle_id", "").casefold():
            continue
        if material_query and material_query != trip.get("material_type", "").casefold():
            continue
        if route_query and route_query != trip.get("route_id", "").casefold():
            continue
        if status_query and status_query != trip.get("trip_status", "").casefold():
            continue
        filtered.append(trip)
    return filtered


def summarize_trips(trips: Iterable[dict]) -> dict:
    trip_list = list(trips)
    completed = [trip for trip in trip_list if trip["trip_status"] == "completed"]
    durations = [
        float(trip["duration_minutes"])
        for trip in completed
        if trip.get("duration_minutes") != ""
    ]
    tonnage_by_material: dict[str, float] = defaultdict(float)
    tonnage_by_route: dict[str, float] = defaultdict(float)
    for trip in completed:
        tons = numeric_tons(trip.get("load_weight_tons"))
        if trip.get("material_type"):
            tonnage_by_material[trip["material_type"]] += tons
        if trip.get("route_id"):
            tonnage_by_route[trip["route_id"]] += tons

    return {
        "total_trips": len(trip_list),
        "completed_trips": len(completed),
        "open_trips": sum(1 for trip in trip_list if trip["trip_status"] == "open"),
        "missing_out_trips": sum(1 for trip in trip_list if trip["trip_status"] == "missing_out"),
        "orphan_out_trips": sum(1 for trip in trip_list if trip["trip_status"] == "orphan_out"),
        "total_completed_tonnage": round(sum(numeric_tons(trip.get("load_weight_tons")) for trip in completed), 2),
        "average_duration_minutes": round(sum(durations) / len(durations), 2) if durations else 0,
        "by_status": dict(sorted(Counter(trip["trip_status"] for trip in trip_list).items())),
        "by_material": dict(sorted(Counter(trip["material_type"] for trip in trip_list if trip["material_type"]).items())),
        "by_route": dict(sorted(Counter(trip["route_id"] for trip in trip_list if trip["route_id"]).items())),
        "tonnage_by_material": {key: round(value, 2) for key, value in sorted(tonnage_by_material.items())},
        "tonnage_by_route": {key: round(value, 2) for key, value in sorted(tonnage_by_route.items())},
    }


def write_trips_csv(trips: Iterable[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=TRIP_FIELDS)
        writer.writeheader()
        for trip in trips:
            writer.writerow({field: trip.get(field, "") for field in TRIP_FIELDS})
    return output_path


def write_trips_summary(trips: Iterable[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summarize_trips(trips), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def write_trips_html(trips: Iterable[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    trip_list = list(trips)
    summary = summarize_trips(trip_list)
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(trip['trip_status'])}</td>"
        f"<td>{escape(trip['vehicle_id'])}</td>"
        f"<td>{escape(trip['driver_name'])}</td>"
        f"<td>{escape(trip['material_type'])}</td>"
        f"<td>{escape(trip['route_id'])}</td>"
        f"<td>{escape(str(trip['duration_minutes']))}</td>"
        f"<td>{escape(str(trip['load_weight_tons']))}</td>"
        "</tr>"
        for trip in trip_list
    )
    if not rows:
        rows = "<tr><td colspan=\"7\">No trips found</td></tr>"

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mining Trip Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2937; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; }}
    th {{ background: #f3f4f6; }}
  </style>
</head>
<body>
  <h1>Mining Trip Report</h1>
  <p>Trips: {summary['total_trips']} | Completed: {summary['completed_trips']} | Open: {summary['open_trips']} | Tonnage: {summary['total_completed_tonnage']}</p>
  <table>
    <thead><tr><th>Status</th><th>Vehicle</th><th>Driver</th><th>Material</th><th>Route</th><th>Duration min</th><th>Tons</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
    return output_path


def export_trips(
    database_dir: Path,
    output_dir: Path,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    vehicle_id: str | None = None,
    material_type: str | None = None,
    route_id: str | None = None,
    trip_status: str | None = None,
) -> dict[str, Path]:
    store = MiningEventStore(database_dir)
    trips = filter_trips(
        reconstruct_trips(store.load_events()),
        date_from=date_from,
        date_to=date_to,
        vehicle_id=vehicle_id,
        material_type=material_type,
        route_id=route_id,
        trip_status=trip_status,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "csv": write_trips_csv(trips, output_dir / "mining_trips.csv"),
        "summary": write_trips_summary(trips, output_dir / "mining_trips_summary.json"),
        "html": write_trips_html(trips, output_dir / "mining_trips_report.html"),
    }
