from __future__ import annotations

from datetime import date

from mining_qr_scanner.payloads import build_qr_payload, payload_checksum, validate_payload_integrity


def vehicle() -> dict:
    return {
        "vehicle_id": "TRUCK-001",
        "plate_number": "MH12MN4101",
        "vehicle_type": "dump_truck",
        "driver_id": "DRV-001",
        "driver_name": "Ramesh Yadav",
        "license_number": "MH-DRV-4101",
        "material_type": "iron_ore",
        "load_status": "loaded",
        "source_zone": "pit-a",
        "destination_zone": "crusher-1",
        "route_id": "route-pit-a-crusher-1",
    }


def test_build_qr_payload_adds_version_dates_id_and_checksum() -> None:
    payload = build_qr_payload(vehicle(), issued_at=date(2026, 7, 10), valid_days=30)

    assert payload["payload_version"] == "1.0"
    assert payload["issued_at"] == "2026-07-10"
    assert payload["expires_on"] == "2026-08-09"
    assert payload["payload_id"].startswith("payload-")
    assert payload["checksum"] == payload_checksum(payload)
    assert validate_payload_integrity(payload, today=date(2026, 7, 10)) == []


def test_validate_payload_integrity_rejects_tampering_and_expiry() -> None:
    payload = build_qr_payload(vehicle(), issued_at=date(2026, 7, 1), valid_days=1)
    payload["vehicle_id"] = "TRUCK-999"

    errors = validate_payload_integrity(payload, today=date(2026, 7, 10))

    assert "checksum mismatch" in errors
    assert "payload expired" in errors


def test_build_qr_payload_can_disable_expiry() -> None:
    payload = build_qr_payload(vehicle(), issued_at=date(2026, 7, 10), valid_days=None)

    assert "expires_on" not in payload
    assert validate_payload_integrity(payload, today=date(2030, 1, 1)) == []
