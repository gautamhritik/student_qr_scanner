from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4


REQUIRED_PAYLOAD_FIELDS = {
    "vehicle_id",
    "plate_number",
    "vehicle_type",
    "driver_id",
    "driver_name",
    "license_number",
    "material_type",
    "load_status",
    "source_zone",
    "destination_zone",
    "route_id",
}
EVENT_DIRECTIONS = {"in", "out"}


def parse_vehicle_payload(payload: str) -> tuple[dict, list[str]]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {"raw_payload": payload}, ["payload is not JSON"]

    if not isinstance(data, dict):
        return {"raw_payload": payload}, ["payload JSON must be an object"]

    errors = [
        f"missing {field}"
        for field in sorted(REQUIRED_PAYLOAD_FIELDS)
        if not str(data.get(field, "")).strip()
    ]
    if "plate_number" in data:
        data["plate_number"] = str(data["plate_number"]).upper().replace(" ", "")
    if "load_status" in data:
        data["load_status"] = str(data["load_status"]).lower().replace(" ", "_")
    return data, errors


def payload_type(payload_info: dict) -> str:
    if payload_info.get("vehicle_id"):
        return "vehicle"
    return "unknown"


def anpr_match_status(payload_info: dict, anpr_plate_number: str | None) -> str:
    if not anpr_plate_number:
        return "not_available"
    qr_plate = str(payload_info.get("plate_number", "")).upper().replace(" ", "")
    anpr_plate = anpr_plate_number.upper().replace(" ", "")
    if not qr_plate:
        return "not_available"
    return "match" if qr_plate == anpr_plate else "mismatch"


def build_scan_event(
    payload: str,
    detection_method: str,
    scanned_at: datetime,
    *,
    site_id: str,
    gate_id: str,
    camera_id: str,
    checkpoint_id: str,
    direction: str,
    readiness: str = "",
    vote_window: int = 1,
    min_votes: int = 1,
    vote_count: int = 1,
    frame_path: str = "",
    scan_status: str | None = None,
    anpr_plate_number: str | None = None,
) -> dict:
    payload_info, validation_errors = parse_vehicle_payload(payload)
    direction = direction.lower().strip()
    if direction not in EVENT_DIRECTIONS:
        validation_errors.append("direction must be in or out")
    final_status = scan_status or ("accepted" if not validation_errors else "validation_failed")
    event = {
        "event_id": uuid4().hex,
        "scanned_at": scanned_at.isoformat(timespec="seconds"),
        "date": scanned_at.strftime("%Y-%m-%d"),
        "time": scanned_at.strftime("%H:%M:%S"),
        "site_id": site_id,
        "gate_id": gate_id,
        "camera_id": camera_id,
        "checkpoint_id": checkpoint_id,
        "direction": direction,
        "detection_method": detection_method,
        "scan_status": final_status,
        "validation_errors": validation_errors,
        "payload_type": payload_type(payload_info),
        "vehicle_id": payload_info.get("vehicle_id", ""),
        "plate_number": payload_info.get("plate_number", ""),
        "vehicle_type": payload_info.get("vehicle_type", ""),
        "owner_operator": payload_info.get("owner_operator", ""),
        "permit_id": payload_info.get("permit_id", ""),
        "rfid_tag": payload_info.get("rfid_tag", ""),
        "driver_id": payload_info.get("driver_id", ""),
        "driver_name": payload_info.get("driver_name", ""),
        "license_number": payload_info.get("license_number", ""),
        "contact_number": payload_info.get("contact_number", ""),
        "company": payload_info.get("company", ""),
        "material_type": payload_info.get("material_type", ""),
        "load_status": payload_info.get("load_status", ""),
        "load_weight_tons": payload_info.get("load_weight_tons", ""),
        "source_zone": payload_info.get("source_zone", ""),
        "destination_zone": payload_info.get("destination_zone", ""),
        "route_id": payload_info.get("route_id", ""),
        "anpr_plate_number": anpr_plate_number or "",
        "anpr_match_status": anpr_match_status(payload_info, anpr_plate_number),
        "readiness": readiness,
        "vote_window": vote_window,
        "min_votes": min_votes,
        "vote_count": vote_count,
        "frame_path": frame_path,
        "qr_info": payload_info,
        "raw_payload": payload,
    }
    return event


class MiningEventStore:
    """JSON-file storage for gate/checkpoint scan events."""

    def __init__(self, database_dir: Path) -> None:
        self.database_dir = database_dir
        self.records_dir = database_dir / "records"
        self.history_file = database_dir / "events.json"
        self.vehicle_state_file = database_dir / "vehicle_state.json"
        self.records_dir.mkdir(parents=True, exist_ok=True)

    def save_event(self, event: dict) -> dict:
        history = self.load_events()
        record = dict(event)
        record["event_number"] = len(history) + 1
        record_path = self.records_dir / self._record_filename(record)
        record["record_file"] = str(record_path)
        self._write_json(record_path, record)
        history.append(record)
        self._write_json(self.history_file, history)
        self._update_vehicle_state(record)
        return record

    def load_events(self) -> list[dict]:
        if not self.history_file.exists():
            return []
        try:
            history = json.loads(self.history_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        return history if isinstance(history, list) else []

    def load_vehicle_state(self) -> dict:
        if not self.vehicle_state_file.exists():
            return {}
        try:
            state = json.loads(self.vehicle_state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return state if isinstance(state, dict) else {}

    def _update_vehicle_state(self, event: dict) -> None:
        if event.get("scan_status") != "accepted" or not event.get("vehicle_id"):
            return
        direction = event.get("direction")
        current_status = "inside" if direction == "in" else "outside" if direction == "out" else "unknown"
        state = self.load_vehicle_state()
        state[event["vehicle_id"]] = {
            "vehicle_id": event.get("vehicle_id", ""),
            "plate_number": event.get("plate_number", ""),
            "current_status": current_status,
            "last_scan_at": event.get("scanned_at", ""),
            "last_direction": direction,
            "last_site_id": event.get("site_id", ""),
            "last_gate_id": event.get("gate_id", ""),
            "last_checkpoint_id": event.get("checkpoint_id", ""),
            "last_camera_id": event.get("camera_id", ""),
            "driver_id": event.get("driver_id", ""),
            "driver_name": event.get("driver_name", ""),
            "material_type": event.get("material_type", ""),
            "load_status": event.get("load_status", ""),
            "load_weight_tons": event.get("load_weight_tons", ""),
            "route_id": event.get("route_id", ""),
            "source_zone": event.get("source_zone", ""),
            "destination_zone": event.get("destination_zone", ""),
        }
        self._write_json(self.vehicle_state_file, state)

    @staticmethod
    def _record_filename(record: dict) -> str:
        identifier = record.get("vehicle_id") or record.get("payload_type") or "unknown"
        slug = "".join(ch if ch.isalnum() else "_" for ch in str(identifier).lower()).strip("_")
        timestamp = str(record["scanned_at"]).replace(":", "-")
        return f"{timestamp}_{slug}_{record['event_id'][:8]}.json"

    @staticmethod
    def _write_json(path: Path, data) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(data, ensure_ascii=False, indent=2)
        with NamedTemporaryFile(
            "w",
            delete=False,
            dir=path.parent,
            encoding="utf-8",
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        temp_path.replace(path)
