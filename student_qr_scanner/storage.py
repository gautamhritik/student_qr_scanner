from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4


class ScanDatabase:
    """Simple JSON-file database for QR scan records."""

    def __init__(self, database_dir: Path) -> None:
        self.database_dir = database_dir
        self.records_dir = database_dir / "records"
        self.history_file = database_dir / "scan_history.json"
        self.records_dir.mkdir(parents=True, exist_ok=True)

    def save_scan(self, payload: str, detection_method: str, scanned_at: datetime) -> dict:
        history = self.load_history()
        record = {
            "scan_id": uuid4().hex,
            "scanned_at": scanned_at.isoformat(timespec="seconds"),
            "date": scanned_at.strftime("%Y-%m-%d"),
            "time": scanned_at.strftime("%H:%M:%S"),
            "detection_method": detection_method,
            "qr_info": self._parse_payload(payload),
        }

        record_path = self.records_dir / self._record_filename(record)
        record["record_file"] = str(record_path)
        record["scan_number"] = len(history) + 1

        self._write_json(record_path, record)
        history.append(record)
        self._write_json(self.history_file, history)
        return record

    def load_history(self) -> list[dict]:
        if not self.history_file.exists():
            return []

        try:
            history = json.loads(self.history_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

        if isinstance(history, list):
            return history
        return []

    @staticmethod
    def _parse_payload(payload: str) -> dict:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return {"raw_payload": payload}

        if isinstance(data, dict):
            return data
        return {"raw_payload": payload}

    @staticmethod
    def _record_filename(record: dict) -> str:
        info = record["qr_info"]
        student_name = str(info.get("name", "unknown_student")).lower()
        slug = "".join(ch if ch.isalnum() else "_" for ch in student_name).strip("_")
        timestamp = record["scanned_at"].replace(":", "-")
        return f"{timestamp}_{slug}_{record['scan_id'][:8]}.json"

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
