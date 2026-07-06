from __future__ import annotations

import pytest

from mining_qr_scanner.fleet import add_vehicle, load_fleet, remove_vehicle


def vehicle(**overrides) -> dict:
    data = {
        "vehicle_id": "TRUCK-100",
        "plate_number": "mh 12 ab 1000",
        "vehicle_type": "dump_truck",
        "owner_operator": "Pit Ops",
        "permit_id": "PERMIT-100",
        "rfid_tag": "RFID-100",
        "driver_id": "DRV-100",
        "driver_name": "Amit Sharma",
        "license_number": "MH-DRV-100",
        "contact_number": "9876543200",
        "company": "Pit Ops",
        "material_type": "iron_ore",
        "load_status": "loaded",
        "load_weight_tons": "32.5",
        "source_zone": "pit-a",
        "destination_zone": "crusher-1",
        "route_id": "route-pit-a-crusher-1",
        "site_id": "mine-1",
        "gate_id": "main-gate",
        "checkpoint_id": "gate-1",
        "status": "active",
    }
    data.update(overrides)
    return data


def test_load_fleet_creates_default_mining_registry(tmp_path) -> None:
    registry = tmp_path / "fleet.json"

    fleet = load_fleet(registry)

    assert registry.exists()
    assert fleet[0]["vehicle_id"] == "TRUCK-001"
    assert fleet[0]["driver_id"]
    assert fleet[0]["material_type"]


def test_add_vehicle_normalizes_plate_load_status_and_rejects_duplicates(tmp_path) -> None:
    registry = tmp_path / "fleet.json"
    created = add_vehicle(registry, vehicle(load_status="Loaded"))

    assert created["plate_number"] == "MH12AB1000"
    assert created["load_status"] == "loaded"
    with pytest.raises(ValueError, match="already exists"):
        add_vehicle(registry, vehicle())


def test_add_vehicle_requires_driver_and_cargo_fields(tmp_path) -> None:
    with pytest.raises(ValueError, match="driver_id"):
        add_vehicle(tmp_path / "fleet.json", vehicle(driver_id=""))


def test_remove_vehicle_deletes_matching_record(tmp_path) -> None:
    registry = tmp_path / "fleet.json"
    add_vehicle(registry, vehicle(vehicle_id="TRUCK-200"))

    removed = remove_vehicle(registry, "truck-200")

    assert removed["vehicle_id"] == "TRUCK-200"
    assert all(item["vehicle_id"] != "TRUCK-200" for item in load_fleet(registry))
