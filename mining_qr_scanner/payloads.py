from __future__ import annotations

from datetime import date, datetime, timedelta
import hashlib
import json
from uuid import uuid5, NAMESPACE_URL

PAYLOAD_VERSION = "1.0"
CHECKSUM_FIELD = "checksum"
INTEGRITY_FIELDS = {CHECKSUM_FIELD}


def canonical_payload(data: dict) -> str:
    unsigned = {key: value for key, value in data.items() if key not in INTEGRITY_FIELDS}
    return json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def payload_checksum(data: dict) -> str:
    return hashlib.sha256(canonical_payload(data).encode("utf-8")).hexdigest()[:16]


def payload_id(vehicle: dict) -> str:
    source = "|".join(
        [
            str(vehicle.get("vehicle_id", "")),
            str(vehicle.get("plate_number", "")),
            str(vehicle.get("driver_id", "")),
            str(vehicle.get("route_id", "")),
            str(vehicle.get("material_type", "")),
        ]
    )
    return f"payload-{uuid5(NAMESPACE_URL, source).hex[:12]}"


def build_qr_payload(
    vehicle: dict,
    *,
    issued_at: date | None = None,
    valid_days: int | None = 365,
) -> dict:
    issued_at = issued_at or datetime.now().astimezone().date()
    payload = dict(vehicle)
    if "plate_number" in payload:
        payload["plate_number"] = str(payload["plate_number"]).upper().replace(" ", "")
    if "load_status" in payload:
        payload["load_status"] = str(payload["load_status"]).lower().replace(" ", "_")
    payload["payload_version"] = PAYLOAD_VERSION
    payload["payload_id"] = payload_id(vehicle)
    payload["issued_at"] = issued_at.isoformat()
    if valid_days is not None:
        if valid_days <= 0:
            raise ValueError("valid_days must be positive when expiry is enabled.")
        payload["expires_on"] = (issued_at + timedelta(days=valid_days)).isoformat()
    else:
        payload.pop("expires_on", None)
    payload[CHECKSUM_FIELD] = payload_checksum(payload)
    return payload


def validate_payload_integrity(payload: dict, *, today: date | None = None) -> list[str]:
    errors = []
    checksum = str(payload.get(CHECKSUM_FIELD, "")).strip()
    if not checksum:
        errors.append("missing checksum")
    elif checksum != payload_checksum(payload):
        errors.append("checksum mismatch")

    version = str(payload.get("payload_version", "")).strip()
    if version != PAYLOAD_VERSION:
        errors.append(f"unsupported payload_version {version!r}")

    expires_on = str(payload.get("expires_on", "")).strip()
    if expires_on:
        try:
            expiry_date = date.fromisoformat(expires_on)
        except ValueError:
            errors.append("expires_on is not a valid ISO date")
        else:
            if (today or datetime.now().astimezone().date()) > expiry_date:
                errors.append("payload expired")
    return errors


def compact_payload_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
