from __future__ import annotations

from html import escape
import json
from pathlib import Path

from mining_qr_scanner.audit import audit_events
from mining_qr_scanner.mining_events import MiningEventStore
from mining_qr_scanner.mining_reports import (
    filter_events,
    summarize_events,
    summarize_vehicle_state,
)
from mining_qr_scanner.opencv_environment import environment_report
from mining_qr_scanner.trips import filter_trips, reconstruct_trips, summarize_trips


def build_operations_summary(
    database_dir: Path,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    include_environment: bool = True,
    stale_inside_hours: float = 12.0,
) -> dict:
    store = MiningEventStore(database_dir)
    all_events = store.load_events()
    events = filter_events(all_events, date_from=date_from, date_to=date_to)
    vehicle_state = store.load_vehicle_state()
    trips = filter_trips(
        reconstruct_trips(all_events),
        date_from=date_from,
        date_to=date_to,
    )
    audit_report = audit_events(
        events,
        vehicle_state,
        stale_inside_hours=stale_inside_hours,
    )
    summary = {
        "filters": {
            "date_from": date_from or "",
            "date_to": date_to or "",
            "stale_inside_hours": stale_inside_hours,
        },
        "events": summarize_events(events),
        "vehicle_state": summarize_vehicle_state(vehicle_state),
        "trips": summarize_trips(trips),
        "audit": {
            "total_issues": audit_report["total_issues"],
            "by_issue_type": audit_report["by_issue_type"],
            "by_severity": audit_report["by_severity"],
            "top_issues": audit_report["issues"][:10],
        },
    }
    if include_environment:
        summary["opencv_environment"] = environment_report()
    return summary


def write_operations_json(summary: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def write_operations_html(summary: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    events = summary["events"]
    vehicles = summary["vehicle_state"]
    trips = summary["trips"]
    audit = summary["audit"]
    environment = summary.get("opencv_environment", {})

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

    issue_rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(issue.get('severity', '')))}</td>"
        f"<td>{escape(str(issue.get('issue_type', '')))}</td>"
        f"<td>{escape(str(issue.get('vehicle_id', '')))}</td>"
        f"<td>{escape(str(issue.get('message', '')))}</td>"
        "</tr>"
        for issue in audit["top_issues"]
    )
    if not issue_rows:
        issue_rows = "<tr><td colspan=\"4\">No audit issues found</td></tr>"

    preview_status = "available" if environment.get("preview_supported") else "unavailable"
    environment_section = ""
    if environment:
        environment_section = (
            "<h2>OpenCV Environment</h2>"
            f"<p>Version: {escape(str(environment.get('cv2_version', 'N/A')))} | "
            f"Preview: {escape(preview_status)} | "
            f"GUI: {escape(str(environment.get('gui_backend', 'N/A')))}</p>"
        )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mining Operations Summary</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2937; }}
    .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin: 20px 0; }}
    .metric {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 12px; }}
    .metric span {{ display: block; color: #6b7280; font-size: 13px; }}
    .metric strong {{ display: block; font-size: 24px; margin-top: 4px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0 28px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; }}
    th {{ background: #f3f4f6; }}
  </style>
</head>
<body>
  <h1>Mining Operations Summary</h1>
  <div class="metrics">
    {metric("Events", events["total_events"])}
    {metric("Unique vehicles", events["unique_vehicles"])}
    {metric("Vehicles inside", vehicles["inside"])}
    {metric("Vehicles outside", vehicles["outside"])}
    {metric("Completed trips", trips["completed_trips"])}
    {metric("Open trips", trips["open_trips"])}
    {metric("Completed tonnage", trips["total_completed_tonnage"])}
    {metric("Audit issues", audit["total_issues"])}
  </div>

  <h2>Trip Tonnage By Material</h2>
  <table><thead><tr><th>Material</th><th>Tons</th></tr></thead><tbody>{count_rows(trips["tonnage_by_material"])}</tbody></table>

  <h2>Events By Gate</h2>
  <table><thead><tr><th>Gate</th><th>Events</th></tr></thead><tbody>{count_rows(events["by_gate"])}</tbody></table>

  <h2>Audit Issues</h2>
  <table><thead><tr><th>Severity</th><th>Type</th><th>Vehicle</th><th>Message</th></tr></thead><tbody>{issue_rows}</tbody></table>

  {environment_section}
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
    return output_path


def export_operations_summary(
    database_dir: Path,
    output_dir: Path,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    include_environment: bool = True,
    stale_inside_hours: float = 12.0,
) -> dict[str, Path]:
    summary = build_operations_summary(
        database_dir,
        date_from=date_from,
        date_to=date_to,
        include_environment=include_environment,
        stale_inside_hours=stale_inside_hours,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "json": write_operations_json(summary, output_dir / "operations_summary.json"),
        "html": write_operations_html(summary, output_dir / "operations_summary.html"),
    }
