from __future__ import annotations

import csv
import json

from generate_vehicle_qrs import generate_vehicle_qr_files, qr_payload, write_fleet_data


def vehicle() -> dict:
    return {
        "vehicle_id": "TRUCK-001",
        "plate_number": "MH12MN4101",
        "vehicle_type": "dump_truck",
        "owner_operator": "Pit Ops",
        "permit_id": "PERMIT-001",
        "rfid_tag": "RFID-001",
        "driver_id": "DRV-001",
        "driver_name": "Ramesh Yadav",
        "license_number": "MH-DRV-4101",
        "contact_number": "9876543210",
        "company": "Pit Ops",
        "material_type": "iron_ore",
        "load_status": "loaded",
        "load_weight_tons": "34.5",
        "source_zone": "pit-a",
        "destination_zone": "crusher-1",
        "route_id": "route-pit-a-crusher-1",
        "site_id": "mine-1",
        "gate_id": "main-gate",
        "checkpoint_id": "gate-1",
        "status": "active",
    }


def test_qr_payload_contains_vehicle_driver_and_cargo_data() -> None:
    payload = qr_payload(vehicle())
    data = json.loads(payload)

    assert data["vehicle_id"] == "TRUCK-001"
    assert data["driver_id"] == "DRV-001"
    assert data["material_type"] == "iron_ore"
    assert ", " not in payload
    assert ": " not in payload


def test_write_fleet_data_writes_csv(tmp_path) -> None:
    write_fleet_data([vehicle()], tmp_path)

    with (tmp_path / "fleet.csv").open("r", encoding="utf-8", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))
    assert rows[0]["vehicle_id"] == "TRUCK-001"
    assert rows[0]["driver_name"] == "Ramesh Yadav"


def test_generate_vehicle_qr_files_clears_old_pngs_and_writes_both_sizes(tmp_path) -> None:
    qr_dir = tmp_path / "qrs"
    large_qr_dir = tmp_path / "large"
    qr_dir.mkdir()
    large_qr_dir.mkdir()
    (qr_dir / "old.png").write_bytes(b"old")
    (large_qr_dir / "old.png").write_bytes(b"old")

    generate_vehicle_qr_files([vehicle()], qr_dir, large_qr_dir)

    assert not (qr_dir / "old.png").exists()
    assert not (large_qr_dir / "old.png").exists()
    assert len(list(qr_dir.glob("*.png"))) == 1
    assert len(list(large_qr_dir.glob("*.png"))) == 1
