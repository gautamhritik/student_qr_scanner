from __future__ import annotations

import argparse
from pathlib import Path

from student_qr_scanner.benchmark import run_benchmark, write_benchmark_outputs

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark QR decoding under simulated mining conditions.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=ROOT / "vehicle_qrs",
        help="Folder containing QR PNG images to benchmark.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "exports" / "qr_condition_benchmark",
        help="Folder for benchmark images and reports.",
    )
    parser.add_argument("--limit", type=int, help="Maximum number of source QR images to test.")
    args = parser.parse_args()

    image_paths = sorted(args.input_dir.glob("*.png"))
    if args.limit is not None:
        if args.limit <= 0:
            raise SystemExit("--limit must be a positive integer.")
        image_paths = image_paths[: args.limit]
    if not image_paths:
        raise SystemExit(f"No PNG QR images found in {args.input_dir}")

    rows = run_benchmark(image_paths, args.output_dir)
    outputs = write_benchmark_outputs(rows, args.output_dir)
    passed = sum(1 for row in rows if row["success"])
    print(f"Benchmark complete: {passed}/{len(rows)} cases decoded.")
    for label, path in outputs.items():
        print(f"- {label}: {path}")


if __name__ == "__main__":
    main()
