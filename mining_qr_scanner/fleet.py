from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile


DEFAULT_FLEET = [
    {
        "vehicle_id": "TRUCK-001",
        "plate_number": "MH12MN4101",
        "vehicle_type": "dump_truck",
        "owner_operator": "Eastern Pit Logistics",
        "permit_id": "PERMIT-HAUL-001",
        "rfid_tag": "RFID-TRUCK-001",
        "driver_id": "DRV-001",
        "driver_name": "Ramesh Yadav",
        "license_number": "MH-DRV-4101",
        "contact_number": "9876543210",
        "company": "Eastern Pit Logistics",
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
    },
    {
        "vehicle_id": "TRUCK-002",
        "plate_number": "MH12MN4102",
        "vehicle_type": "tipper_truck",
        "owner_operator": "Mine Operations",
        "permit_id": "PERMIT-HAUL-002",
        "rfid_tag": "RFID-TRUCK-002",
        "driver_id": "DRV-002",
        "driver_name": "Suresh Patil",
        "license_number": "MH-DRV-4102",
        "contact_number": "9876543211",
        "company": "Mine Operations",
        "material_type": "coal",
        "load_status": "loaded",
        "load_weight_tons": "28.0",
        "source_zone": "pit-b",
        "destination_zone": "stockyard-2",
        "route_id": "route-pit-b-stockyard-2",
        "site_id": "mine-1",
        "gate_id": "west-gate",
        "checkpoint_id": "gate-2",
        "status": "active",
    },
    {
        "vehicle_id": "WATER-007",
        "plate_number": "MH12MN7782",
        "vehicle_type": "water_tanker",
        "owner_operator": "Dust Control Team",
        "permit_id": "PERMIT-WATER-007",
        "rfid_tag": "RFID-WATER-007",
        "driver_id": "DRV-007",
        "driver_name": "Imran Khan",
        "license_number": "MH-DRV-7782",
        "contact_number": "9876543212",
        "company": "Dust Control Team",
        "material_type": "water",
        "load_status": "loaded",
        "load_weight_tons": "18.0",
        "source_zone": "service-yard",
        "destination_zone": "haul-road",
        "route_id": "route-yard-haul-road",
        "site_id": "mine-1",
        "gate_id": "service-gate",
        "checkpoint_id": "service-gate",
        "status": "active",
    },
]

FLEET_FIELDS = [
    "vehicle_id",
    "plate_number",
    "vehicle_type",
    "owner_operator",
    "permit_id",
    "rfid_tag",
    "driver_id",
    "driver_name",
    "license_number",
    "contact_number",
    "company",
    "material_type",
    "load_status",
    "load_weight_tons",
    "source_zone",
    "destination_zone",
    "route_id",
    "site_id",
    "gate_id",
    "checkpoint_id",
    "status",
]

REQUIRED_FIELDS = {
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


def normalize_vehicle(vehicle: dict) -> dict:
    normalized = {field: str(vehicle.get(field, "")).strip() for field in FLEET_FIELDS}
    missing = [field for field in sorted(REQUIRED_FIELDS) if not normalized[field]]
    if missing:
        raise ValueError(f"Missing required fleet fields: {', '.join(missing)}")
    normalized["plate_number"] = normalized["plate_number"].upper().replace(" ", "")
    normalized["status"] = normalized["status"] or "active"
    normalized["load_status"] = normalized["load_status"].lower().replace(" ", "_")
    return normalized


def vehicle_key(vehicle: dict) -> str:
    return normalize_vehicle(vehicle)["vehicle_id"].casefold()


def load_fleet(registry_path: Path, *, create_from_defaults: bool = True) -> list[dict]:
    if not registry_path.exists():
        fleet = [normalize_vehicle(vehicle) for vehicle in DEFAULT_FLEET]
        if create_from_defaults:
            save_fleet(registry_path, fleet)
        return fleet

    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Fleet registry is not valid JSON: {registry_path}") from exc

    if not isinstance(data, list):
        raise ValueError("Fleet registry must contain a list of vehicles.")
    return [normalize_vehicle(vehicle) for vehicle in data]


def save_fleet(registry_path: Path, fleet: list[dict]) -> Path:
    normalized = [normalize_vehicle(vehicle) for vehicle in fleet]
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(normalized, ensure_ascii=False, indent=2)
    temp_path = None
    with NamedTemporaryFile(
        "w",
        delete=False,
        dir=registry_path.parent,
        encoding="utf-8",
        prefix=f".{registry_path.name}.",
        suffix=".tmp",
    ) as temp_file:
        temp_file.write(content)
        temp_path = Path(temp_file.name)
    try:
        temp_path.replace(registry_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    return registry_path


def add_vehicle(registry_path: Path, vehicle: dict) -> dict:
    fleet = load_fleet(registry_path)
    new_vehicle = normalize_vehicle(vehicle)
    key = vehicle_key(new_vehicle)
    if any(vehicle_key(existing) == key for existing in fleet):
        raise ValueError(f"Vehicle already exists: {new_vehicle['vehicle_id']}")
    fleet.append(new_vehicle)
    save_fleet(registry_path, fleet)
    return new_vehicle


def remove_vehicle(registry_path: Path, vehicle_id: str) -> dict:
    fleet = load_fleet(registry_path)
    query = vehicle_id.casefold()
    kept = [vehicle for vehicle in fleet if vehicle["vehicle_id"].casefold() != query]
    if len(kept) == len(fleet):
        raise ValueError(f"Vehicle not found: {vehicle_id}")
    removed = next(vehicle for vehicle in fleet if vehicle["vehicle_id"].casefold() == query)
    save_fleet(registry_path, kept)
    return removed
