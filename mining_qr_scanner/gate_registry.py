from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile


GATE_FIELDS = [
    "site_id",
    "gate_id",
    "checkpoint_id",
    "camera_id",
    "allowed_directions",
    "camera_role",
    "stream_hint",
    "location",
    "status",
    "notes",
]

DEFAULT_GATES = [
    {
        "site_id": "mine-1",
        "gate_id": "main-gate",
        "checkpoint_id": "gate-1",
        "camera_id": "pole-cam-1",
        "allowed_directions": ["in", "out"],
        "camera_role": "entry_exit",
        "stream_hint": "camera-index-0",
        "location": "main haul road gate",
        "status": "active",
        "notes": "Primary pole camera for loaded truck movement.",
    },
    {
        "site_id": "mine-1",
        "gate_id": "west-gate",
        "checkpoint_id": "gate-2",
        "camera_id": "pole-cam-2",
        "allowed_directions": ["in", "out"],
        "camera_role": "entry_exit",
        "stream_hint": "rtsp://west-gate-camera",
        "location": "west pit access road",
        "status": "active",
        "notes": "Secondary gate for pit-b and stockyard movement.",
    },
    {
        "site_id": "mine-1",
        "gate_id": "service-gate",
        "checkpoint_id": "service-gate",
        "camera_id": "service-cam-1",
        "allowed_directions": ["in", "out"],
        "camera_role": "service_yard",
        "stream_hint": "camera-index-1",
        "location": "service yard exit",
        "status": "active",
        "notes": "Water tankers and maintenance vehicles.",
    },
]


def normalize_gate(gate: dict) -> dict:
    normalized = {field: gate.get(field, "") for field in GATE_FIELDS}
    for field in GATE_FIELDS:
        if field != "allowed_directions":
            normalized[field] = str(normalized[field]).strip()

    missing = [
        field
        for field in ("site_id", "gate_id", "checkpoint_id", "camera_id")
        if not normalized[field]
    ]
    if missing:
        raise ValueError(f"Missing required gate fields: {', '.join(missing)}")

    directions = normalized["allowed_directions"]
    if isinstance(directions, str):
        directions = [value.strip() for value in directions.split(",") if value.strip()]
    if not isinstance(directions, list):
        raise ValueError("allowed_directions must be a list or comma-separated string.")
    normalized["allowed_directions"] = sorted({str(value).lower().strip() for value in directions if str(value).strip()})
    invalid = [value for value in normalized["allowed_directions"] if value not in {"in", "out"}]
    if invalid:
        raise ValueError(f"Invalid directions: {', '.join(invalid)}")
    if not normalized["allowed_directions"]:
        normalized["allowed_directions"] = ["in", "out"]
    normalized["status"] = normalized["status"] or "active"
    return normalized


def gate_key(gate: dict) -> tuple[str, str, str, str]:
    normalized = normalize_gate(gate)
    return (
        normalized["site_id"].casefold(),
        normalized["gate_id"].casefold(),
        normalized["checkpoint_id"].casefold(),
        normalized["camera_id"].casefold(),
    )


def load_gates(registry_path: Path, *, create_from_defaults: bool = True) -> list[dict]:
    if not registry_path.exists():
        gates = [normalize_gate(gate) for gate in DEFAULT_GATES]
        if create_from_defaults:
            save_gates(registry_path, gates)
        return gates

    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gate registry is not valid JSON: {registry_path}") from exc
    if not isinstance(data, list):
        raise ValueError("Gate registry must contain a list of gate camera records.")
    return [normalize_gate(gate) for gate in data]


def save_gates(registry_path: Path, gates: list[dict]) -> Path:
    normalized = [normalize_gate(gate) for gate in gates]
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


def add_gate(registry_path: Path, gate: dict) -> dict:
    gates = load_gates(registry_path)
    new_gate = normalize_gate(gate)
    key = gate_key(new_gate)
    if any(gate_key(existing) == key for existing in gates):
        raise ValueError(f"Gate camera already exists: {new_gate['gate_id']} / {new_gate['camera_id']}")
    gates.append(new_gate)
    save_gates(registry_path, gates)
    return new_gate


def remove_gate(registry_path: Path, *, site_id: str, gate_id: str, checkpoint_id: str, camera_id: str) -> dict:
    gates = load_gates(registry_path)
    query = (
        site_id.casefold(),
        gate_id.casefold(),
        checkpoint_id.casefold(),
        camera_id.casefold(),
    )
    kept = [gate for gate in gates if gate_key(gate) != query]
    if len(kept) == len(gates):
        raise ValueError(f"Gate camera not found: {gate_id} / {camera_id}")
    removed = next(gate for gate in gates if gate_key(gate) == query)
    save_gates(registry_path, kept)
    return removed


def find_gate(
    gates: list[dict],
    *,
    site_id: str,
    gate_id: str,
    checkpoint_id: str,
    camera_id: str,
) -> dict | None:
    query = (
        site_id.casefold(),
        gate_id.casefold(),
        checkpoint_id.casefold(),
        camera_id.casefold(),
    )
    for gate in gates:
        if gate_key(gate) == query:
            return gate
    return None


def validate_scanner_assignment(
    registry_path: Path,
    *,
    site_id: str,
    gate_id: str,
    checkpoint_id: str,
    camera_id: str,
    direction: str,
) -> dict:
    gates = load_gates(registry_path)
    gate = find_gate(
        gates,
        site_id=site_id,
        gate_id=gate_id,
        checkpoint_id=checkpoint_id,
        camera_id=camera_id,
    )
    if gate is None:
        raise ValueError(
            "Scanner assignment is not registered: "
            f"{site_id}/{gate_id}/{checkpoint_id}/{camera_id}"
        )
    if direction.lower() not in gate["allowed_directions"]:
        raise ValueError(
            f"Direction {direction!r} is not allowed for gate {gate_id}; "
            f"allowed: {', '.join(gate['allowed_directions'])}"
        )
    if gate["status"].casefold() != "active":
        raise ValueError(f"Gate camera is not active: {gate_id} / {camera_id}")
    return gate
