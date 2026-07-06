from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile


DEFAULT_FLEET = [
    {
        "vehicle_id": "TRUCK-001",
        "plate_number": "MH12MN4101",
        "vehicle_type": "haul_truck",
        "owner_operator": "Eastern Pit Logistics",
        "site": "north-pit",
        "assigned_route": "ore-face-to-crusher",
        "checkpoint_id": "gate-1",
        "status": "active",
    },
    {
        "vehicle_id": "EXC-014",
        "plate_number": "MH12MN6214",
        "vehicle_type": "excavator",
        "owner_operator": "Mine Operations",
        "site": "north-pit",
        "assigned_route": "bench-3",
        "checkpoint_id": "pit-entry",
        "status": "active",
    },
    {
        "vehicle_id": "WATER-007",
        "plate_number": "MH12MN7782",
        "vehicle_type": "water_tanker",
        "owner_operator": "Dust Control Team",
        "site": "south-yard",
        "assigned_route": "yard-to-haul-road",
        "checkpoint_id": "service-gate",
        "status": "active",
    },
    {
        "vehicle_id": "DOZER-003",
        "plate_number": "MH12MN3303",
        "vehicle_type": "dozer",
        "owner_operator": "Mine Operations",
        "site": "north-pit",
        "assigned_route": "waste-dump",
        "checkpoint_id": "dump-entry",
        "status": "maintenance",
    },
]

FLEET_FIELDS = [
    "vehicle_id",
    "plate_number",
    "vehicle_type",
    "owner_operator",
    "site",
    "assigned_route",
    "checkpoint_id",
    "status",
]


def normalize_vehicle(vehicle: dict) -> dict:
    normalized = {field: str(vehicle.get(field, "")).strip() for field in FLEET_FIELDS}
    if not normalized["vehicle_id"]:
        raise ValueError("vehicle_id is required.")
    if not normalized["plate_number"]:
        raise ValueError("plate_number is required.")
    if not normalized["vehicle_type"]:
        raise ValueError("vehicle_type is required.")
    normalized["plate_number"] = normalized["plate_number"].upper().replace(" ", "")
    normalized["status"] = normalized["status"] or "active"
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
    temp_path.replace(registry_path)
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
