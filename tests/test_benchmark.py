from __future__ import annotations

from generate_vehicle_qrs import make_qr
from student_qr_scanner.benchmark import run_benchmark, summarize_results, write_benchmark_outputs


def test_benchmark_runs_conditions_and_writes_outputs(tmp_path) -> None:
    qr_path = tmp_path / "vehicle.png"
    make_qr('{"vehicle_id":"TRUCK-001","plate_number":"MH12MN4101","vehicle_type":"haul_truck"}', qr_path)

    rows = run_benchmark([qr_path], tmp_path / "benchmark")
    outputs = write_benchmark_outputs(rows, tmp_path / "benchmark")
    summary = summarize_results(rows)

    assert len(rows) == 8
    assert any(row["condition"] == "clean" and row["success"] for row in rows)
    assert summary["total_cases"] == 8
    assert outputs["csv"].exists()
    assert outputs["summary"].exists()
    assert outputs["html"].exists()
