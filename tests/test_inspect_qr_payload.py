from __future__ import annotations

import json
from datetime import date

import inspect_qr_payload
from mining_qr_scanner.payloads import build_qr_payload


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


def test_inspect_payload_file_prints_json_result(tmp_path, capsys) -> None:
    payload_path = tmp_path / "payload.txt"
    payload_path.write_text(
        json.dumps(build_qr_payload(vehicle(), issued_at=date(2026, 7, 10))),
        encoding="utf-8",
    )

    original_parse_args = inspect_qr_payload.argparse.ArgumentParser.parse_args

    def fake_parse_args(self):
        return type(
            "Args",
            (),
            {
                "image": None,
                "payload_file": payload_path,
                "payload": None,
                "json": True,
            },
        )()

    inspect_qr_payload.argparse.ArgumentParser.parse_args = fake_parse_args
    try:
        inspect_qr_payload.main()
    finally:
        inspect_qr_payload.argparse.ArgumentParser.parse_args = original_parse_args

    output = json.loads(capsys.readouterr().out)
    assert output["valid"] is True
    assert output["payload"]["vehicle_id"] == "TRUCK-001"
