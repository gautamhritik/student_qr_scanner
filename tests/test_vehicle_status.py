from __future__ import annotations

import csv

from vehicle_status import filter_state, write_state_csv


def state() -> dict:
    return {
        "TRUCK-001": {
            "vehicle_id": "TRUCK-001",
            "plate_number": "MH12MN4101",
            "current_status": "inside",
            "last_scan_at": "2026-07-07T10:00:00+05:30",
            "last_direction": "in",
            "last_gate_id": "main-gate",
            "last_checkpoint_id": "gate-1",
            "last_camera_id": "pole-cam-1",
            "driver_id": "DRV-001",
            "driver_name": "Ramesh Yadav",
            "material_type": "iron_ore",
            "load_status": "loaded",
            "load_weight_tons": "34.5",
            "route_id": "route-pit-a-crusher-1",
            "source_zone": "pit-a",
            "destination_zone": "crusher-1",
        },
        "TRUCK-002": {
            "vehicle_id": "TRUCK-002",
            "plate_number": "MH12MN4102",
            "current_status": "outside",
            "last_gate_id": "west-gate",
            "material_type": "coal",
        },
    }


def test_filter_state_by_status_gate_and_material() -> None:
    rows = filter_state(state(), status="inside", gate_id="main-gate", material_type="iron_ore")

    assert len(rows) == 1
    assert rows[0]["vehicle_id"] == "TRUCK-001"


def test_write_state_csv(tmp_path) -> None:
    rows = filter_state(state())
    output_path = write_state_csv(rows, tmp_path / "vehicle_state.csv")

    with output_path.open("r", encoding="utf-8", newline="") as csv_file:
        csv_rows = list(csv.DictReader(csv_file))

    assert csv_rows[0]["vehicle_id"]
    assert {row["current_status"] for row in csv_rows} == {"inside", "outside"}
