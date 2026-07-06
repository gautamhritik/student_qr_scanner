from __future__ import annotations

import json

import numpy as np

from student_qr_scanner.scanner import LightingAdaptiveQRScanner, format_payload


def test_format_payload_formats_student_json() -> None:
    payload = json.dumps(
        {
            "name": "Aarav Mehta",
            "class": "8A",
            "roll_no": 11,
            "age": 13,
            "class_teacher": "Mrs. Kavita Sharma",
        }
    )

    assert format_payload(payload).splitlines() == [
        "Name: Aarav Mehta",
        "Class: 8A",
        "Roll No: 11",
        "Age: 13",
        "Class Teacher: Mrs. Kavita Sharma",
    ]


def test_format_payload_formats_vehicle_json() -> None:
    payload = json.dumps(
        {
            "vehicle_id": "TRUCK-001",
            "plate_number": "MH12MN4101",
            "vehicle_type": "haul_truck",
            "owner_operator": "Pit Ops",
            "site": "north-pit",
            "assigned_route": "gate-to-crusher",
            "checkpoint_id": "gate-1",
            "status": "active",
        }
    )

    assert format_payload(payload).splitlines() == [
        "Vehicle/Equipment ID: TRUCK-001",
        "Plate Number: MH12MN4101",
        "Type: haul_truck",
        "Owner/Operator: Pit Ops",
        "Site: north-pit",
        "Route/Checkpoint: gate-to-crusher / gate-1",
        "Status: active",
    ]


def test_format_payload_returns_raw_text_for_invalid_json() -> None:
    assert format_payload("plain qr text") == "plain qr text"


def test_digital_zoom_keeps_frame_shape() -> None:
    frame = np.arange(100 * 120 * 3, dtype=np.uint8).reshape(100, 120, 3)

    zoomed = LightingAdaptiveQRScanner.digital_zoom(frame, 2.0)

    assert zoomed.shape == frame.shape


def test_digital_zoom_returns_original_for_no_zoom() -> None:
    frame = np.zeros((20, 30, 3), dtype=np.uint8)

    assert LightingAdaptiveQRScanner.digital_zoom(frame, 1.0) is frame


def test_estimate_distance_readiness_messages() -> None:
    frame = np.zeros((1000, 1200, 3), dtype=np.uint8)
    small_points = np.array([[[0, 0], [50, 0], [50, 50], [0, 50]]], dtype=np.float32)
    medium_points = np.array([[[0, 0], [100, 0], [100, 100], [0, 100]]], dtype=np.float32)
    large_points = np.array([[[0, 0], [180, 0], [180, 180], [0, 180]]], dtype=np.float32)

    assert "very small" in LightingAdaptiveQRScanner.estimate_distance_readiness(
        small_points, frame
    )
    assert "readable but small" in LightingAdaptiveQRScanner.estimate_distance_readiness(
        medium_points, frame
    )
    assert LightingAdaptiveQRScanner.estimate_distance_readiness(large_points, frame) == (
        "QR size in frame looks good."
    )
