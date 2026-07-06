from __future__ import annotations

import pytest

from student_qr_scanner.fleet import add_vehicle, load_fleet, remove_vehicle


def vehicle(**overrides) -> dict:
    data = {
        "vehicle_id": "TRUCK-100",
        "plate_number": "mh 12 ab 1000",
        "vehicle_type": "haul_truck",
        "owner_operator": "Pit Ops",
        "site": "north-pit",
        "assigned_route": "gate-to-crusher",
        "checkpoint_id": "gate-1",
        "status": "active",
    }
    data.update(overrides)
    return data


def test_load_fleet_creates_default_registry(tmp_path) -> None:
    registry = tmp_path / "fleet.json"

    fleet = load_fleet(registry)

    assert registry.exists()
    assert fleet[0]["vehicle_id"] == "TRUCK-001"


def test_add_vehicle_normalizes_plate_and_rejects_duplicates(tmp_path) -> None:
    registry = tmp_path / "fleet.json"
    created = add_vehicle(registry, vehicle())

    assert created["plate_number"] == "MH12AB1000"
    with pytest.raises(ValueError, match="already exists"):
        add_vehicle(registry, vehicle())


def test_remove_vehicle_deletes_matching_record(tmp_path) -> None:
    registry = tmp_path / "fleet.json"
    add_vehicle(registry, vehicle(vehicle_id="TRUCK-200"))

    removed = remove_vehicle(registry, "truck-200")

    assert removed["vehicle_id"] == "TRUCK-200"
    assert all(item["vehicle_id"] != "TRUCK-200" for item in load_fleet(registry))
