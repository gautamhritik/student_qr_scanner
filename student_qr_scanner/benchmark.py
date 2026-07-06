from __future__ import annotations

import csv
from collections import Counter
from html import escape
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from student_qr_scanner.scanner import LightingAdaptiveQRScanner


CONDITIONS = [
    "clean",
    "low_light",
    "blur",
    "glare",
    "dust",
    "rotation",
    "distance_scale",
    "crop",
]


def condition_variants(image: Image.Image) -> dict[str, Image.Image]:
    base = image.convert("RGB")
    variants: dict[str, Image.Image] = {"clean": base}
    variants["low_light"] = ImageEnhance.Brightness(base).enhance(0.32)
    variants["blur"] = base.filter(ImageFilter.GaussianBlur(radius=2.0))

    glare = base.copy()
    draw = ImageDraw.Draw(glare, "RGBA")
    w, h = glare.size
    draw.ellipse((w * 0.45, h * 0.10, w * 1.05, h * 0.65), fill=(255, 255, 255, 120))
    variants["glare"] = glare

    rng = np.random.default_rng(42)
    dust = np.array(base).astype(np.uint8)
    mask = rng.random(dust.shape[:2]) < 0.08
    dust[mask] = np.array([170, 160, 130], dtype=np.uint8)
    variants["dust"] = Image.fromarray(dust)

    variants["rotation"] = base.rotate(10, expand=True, fillcolor="white")

    canvas_size = max(base.size)
    small = base.resize((max(24, canvas_size // 5), max(24, canvas_size // 5)), Image.Resampling.BICUBIC)
    canvas = Image.new("RGB", (canvas_size, canvas_size), "white")
    canvas.paste(small, ((canvas_size - small.width) // 2, (canvas_size - small.height) // 2))
    variants["distance_scale"] = canvas

    crop_margin = int(min(base.size) * 0.08)
    variants["crop"] = base.crop((crop_margin, crop_margin, base.width, base.height))
    return variants


def pil_to_bgr(image: Image.Image) -> np.ndarray:
    rgb = np.array(image.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def run_benchmark(
    image_paths: list[Path],
    output_dir: Path,
    *,
    scanner: LightingAdaptiveQRScanner | None = None,
) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    variants_dir = output_dir / "condition_images"
    variants_dir.mkdir(parents=True, exist_ok=True)
    scanner = scanner or LightingAdaptiveQRScanner()
    rows = []

    for image_path in image_paths:
        image = Image.open(image_path)
        for condition, variant in condition_variants(image).items():
            variant_path = variants_dir / f"{image_path.stem}_{condition}.png"
            variant.save(variant_path)
            result = scanner.detect(pil_to_bgr(variant))
            payload = result[0] if result else ""
            method = result[2] if result else ""
            rows.append(
                {
                    "source_image": str(image_path),
                    "condition": condition,
                    "success": bool(result),
                    "detection_method": method,
                    "payload_preview": payload[:120],
                    "variant_image": str(variant_path),
                }
            )
    return rows


def summarize_results(rows: list[dict]) -> dict:
    by_condition = {}
    for condition in CONDITIONS:
        condition_rows = [row for row in rows if row["condition"] == condition]
        passed = sum(1 for row in condition_rows if row["success"])
        by_condition[condition] = {
            "total": len(condition_rows),
            "passed": passed,
            "failed": len(condition_rows) - passed,
            "success_rate": round(passed / len(condition_rows), 3) if condition_rows else 0.0,
        }
    methods = Counter(row["detection_method"] for row in rows if row["detection_method"])
    total_passed = sum(1 for row in rows if row["success"])
    return {
        "total_cases": len(rows),
        "passed": total_passed,
        "failed": len(rows) - total_passed,
        "overall_success_rate": round(total_passed / len(rows), 3) if rows else 0.0,
        "by_condition": by_condition,
        "by_detection_method": dict(sorted(methods.items())),
    }


def write_benchmark_outputs(rows: list[dict], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "qr_condition_benchmark.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "source_image",
                "condition",
                "success",
                "detection_method",
                "payload_preview",
                "variant_image",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize_results(rows)
    summary_path = output_dir / "qr_condition_benchmark_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    rows_html = "\n".join(
        "<tr>"
        f"<td>{escape(Path(row['source_image']).name)}</td>"
        f"<td>{escape(str(row['condition']))}</td>"
        f"<td>{'yes' if row['success'] else 'no'}</td>"
        f"<td>{escape(str(row['detection_method']))}</td>"
        "</tr>"
        for row in rows
    )
    if not rows_html:
        rows_html = "<tr><td colspan=\"4\">No benchmark rows</td></tr>"
    html_path = output_dir / "qr_condition_benchmark.html"
    html_path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>QR Condition Benchmark</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2937; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; }}
    th {{ background: #f3f4f6; }}
  </style>
</head>
<body>
  <h1>QR Condition Benchmark</h1>
  <p>Total cases: {summary['total_cases']} | Passed: {summary['passed']} | Failed: {summary['failed']} | Success rate: {summary['overall_success_rate']}</p>
  <table>
    <thead><tr><th>Image</th><th>Condition</th><th>Decoded</th><th>Method</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</body>
</html>
""",
        encoding="utf-8",
    )
    return {"csv": csv_path, "summary": summary_path, "html": html_path}
