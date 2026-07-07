from __future__ import annotations

import pytest

from mining_qr_scanner.gate_registry import (
    add_gate,
    load_gates,
    remove_gate,
    validate_scanner_assignment,
)


def gate(**overrides) -> dict:
    data = {
        "site_id": "mine-1",
        "gate_id": "north-gate",
        "checkpoint_id": "gate-3",
        "camera_id": "pole-cam-3",
        "allowed_directions": "in,out",
        "camera_role": "entry_exit",
        "stream_hint": "camera-index-3",
        "location": "north haul road",
        "status": "active",
        "notes": "Test gate",
    }
    data.update(overrides)
    return data


def test_load_gates_creates_default_registry(tmp_path) -> None:
    registry = tmp_path / "gates.json"

    gates = load_gates(registry)

    assert registry.exists()
    assert gates[0]["gate_id"] == "main-gate"
    assert "in" in gates[0]["allowed_directions"]


def test_add_gate_normalizes_directions_and_rejects_duplicates(tmp_path) -> None:
    registry = tmp_path / "gates.json"
    created = add_gate(registry, gate(allowed_directions="out,in"))

    assert created["allowed_directions"] == ["in", "out"]
    with pytest.raises(ValueError, match="already exists"):
        add_gate(registry, gate())


def test_validate_scanner_assignment_accepts_registered_active_direction(tmp_path) -> None:
    registry = tmp_path / "gates.json"
    add_gate(registry, gate())

    validated = validate_scanner_assignment(
        registry,
        site_id="mine-1",
        gate_id="north-gate",
        checkpoint_id="gate-3",
        camera_id="pole-cam-3",
        direction="in",
    )

    assert validated["camera_role"] == "entry_exit"


def test_validate_scanner_assignment_rejects_unregistered_or_wrong_direction(tmp_path) -> None:
    registry = tmp_path / "gates.json"
    add_gate(registry, gate(allowed_directions="in"))

    with pytest.raises(ValueError, match="not allowed"):
        validate_scanner_assignment(
            registry,
            site_id="mine-1",
            gate_id="north-gate",
            checkpoint_id="gate-3",
            camera_id="pole-cam-3",
            direction="out",
        )


def test_remove_gate_deletes_matching_camera(tmp_path) -> None:
    registry = tmp_path / "gates.json"
    add_gate(registry, gate())

    removed = remove_gate(
        registry,
        site_id="mine-1",
        gate_id="north-gate",
        checkpoint_id="gate-3",
        camera_id="pole-cam-3",
    )

    assert removed["gate_id"] == "north-gate"
    assert all(item["gate_id"] != "north-gate" for item in load_gates(registry))
