from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4


REQUIRED_VEHICLE_FIELDS = {"vehicle_id", "plate_number", "vehicle_type"}


def parse_vehicle_payload(payload: str) -> tuple[dict, list[str]]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {"raw_payload": payload}, ["payload is not JSON"]

    if not isinstance(data, dict):
        return {"raw_payload": payload}, ["payload JSON must be an object"]

    errors = [
        f"missing {field}"
        for field in sorted(REQUIRED_VEHICLE_FIELDS)
        if not str(data.get(field, "")).strip()
    ]
    if "plate_number" in data:
        data["plate_number"] = str(data["plate_number"]).upper().replace(" ", "")
    return data, errors


def payload_type(payload_info: dict) -> str:
    if payload_info.get("vehicle_id"):
        return "vehicle"
    if payload_info.get("name") and payload_info.get("roll_no"):
        return "student"
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
    camera_id: str,
    checkpoint_id: str,
    readiness: str = "",
    anpr_plate_number: str | None = None,
) -> dict:
    payload_info, validation_errors = parse_vehicle_payload(payload)
    scan_status = "accepted" if not validation_errors else "validation_failed"
    event = {
        "event_id": uuid4().hex,
        "scanned_at": scanned_at.isoformat(timespec="seconds"),
        "date": scanned_at.strftime("%Y-%m-%d"),
        "time": scanned_at.strftime("%H:%M:%S"),
        "camera_id": camera_id,
        "checkpoint_id": checkpoint_id,
        "detection_method": detection_method,
        "scan_status": scan_status,
        "validation_errors": validation_errors,
        "payload_type": payload_type(payload_info),
        "vehicle_id": payload_info.get("vehicle_id", ""),
        "plate_number": payload_info.get("plate_number", ""),
        "vehicle_type": payload_info.get("vehicle_type", ""),
        "site": payload_info.get("site", ""),
        "assigned_route": payload_info.get("assigned_route", ""),
        "owner_operator": payload_info.get("owner_operator", ""),
        "anpr_plate_number": anpr_plate_number or "",
        "anpr_match_status": anpr_match_status(payload_info, anpr_plate_number),
        "readiness": readiness,
        "qr_info": payload_info,
        "raw_payload": payload,
    }
    return event


class MiningEventStore:
    """JSON-file storage for gate/checkpoint scan events."""

    def __init__(self, database_dir: Path) -> None:
        self.database_dir = database_dir
        self.records_dir = database_dir / "records"
        self.history_file = database_dir / "scan_events.json"
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
        return record

    def load_events(self) -> list[dict]:
        if not self.history_file.exists():
            return []
        try:
            history = json.loads(self.history_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        return history if isinstance(history, list) else []

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
