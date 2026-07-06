from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Iterable

import cv2
import numpy as np


@dataclass(frozen=True)
class FrameVariant:
    method: str
    image: np.ndarray
    scale_x: float = 1.0
    scale_y: float = 1.0
    offset_x: int = 0
    offset_y: int = 0


class LightingAdaptiveQRScanner:
    """QR scanner that retries decoding with distance and lighting variants."""

    def __init__(self) -> None:
        self.detector = cv2.QRCodeDetector()
        self.detector.setEpsX(0.20)
        self.detector.setEpsY(0.20)

    def detect(self, frame: np.ndarray) -> tuple[str, np.ndarray | None, str] | None:
        for variant in self._variants(frame):
            result = self._decode(variant)
            if result:
                return result
        return None

    def _decode(self, variant: FrameVariant) -> tuple[str, np.ndarray | None, str] | None:
        payload, points, _ = self.detector.detectAndDecode(variant.image)
        if payload:
            return payload, self._map_points(points, variant), variant.method

        return None

    def _variants(self, frame: np.ndarray) -> Iterable[FrameVariant]:
        for source in self._sources(frame):
            yield from self._enhanced_variants(source)

    def _sources(self, frame: np.ndarray) -> Iterable[FrameVariant]:
        yield FrameVariant("full-frame", frame)

        h, w = frame.shape[:2]
        if max(h, w) < 900:
            scale = 0.75
            resampled = cv2.resize(
                frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA
            )
            yield FrameVariant("resampled-small-input", resampled, scale_x=scale, scale_y=scale)

        if max(h, w) < 900:
            pad = max(16, int(min(h, w) * 0.08))
            padded = cv2.copyMakeBorder(
                frame, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(255, 255, 255)
            )
            yield FrameVariant("white-padded", padded, offset_x=-pad, offset_y=-pad)

        # Distant QR codes are usually centered by the person scanning. These
        # crops act like digital zoom while still preserving mapped box points.
        for crop_ratio in (0.70, 0.50, 0.35):
            cropped, offset_x, offset_y = self._center_crop(frame, crop_ratio)
            yield FrameVariant(
                f"center-crop-{int(crop_ratio * 100)}",
                cropped,
                offset_x=offset_x,
                offset_y=offset_y,
            )

    def _enhanced_variants(self, source: FrameVariant) -> Iterable[FrameVariant]:
        frame = source.image
        yield source

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        yield self._copy_variant(source, "grayscale", gray)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast = clahe.apply(gray)
        yield self._copy_variant(source, "contrast-normalized", contrast)

        for gamma in (0.55, 1.8):
            yield self._copy_variant(source, f"gamma-{gamma}", self._gamma(gray, gamma))

        blurred = cv2.GaussianBlur(contrast, (0, 0), 1.2)
        sharpened = cv2.addWeighted(contrast, 1.6, blurred, -0.6, 0)
        yield self._copy_variant(source, "sharpened", sharpened)

        _, otsu = cv2.threshold(
            contrast, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        yield self._copy_variant(source, "otsu-threshold", otsu)

        h, w = gray.shape[:2]
        if max(h, w) < 1400:
            adaptive = cv2.adaptiveThreshold(
                contrast,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                31,
                4,
            )
            yield self._copy_variant(source, "adaptive-threshold", adaptive)

        if source.method != "full-frame" and max(h, w) < 1400:
            for scale in (2.0, 3.0):
                upscaled = cv2.resize(
                    contrast,
                    None,
                    fx=scale,
                    fy=scale,
                    interpolation=cv2.INTER_CUBIC,
                )
                yield FrameVariant(
                    f"{source.method}-upscaled-{scale:g}x",
                    upscaled,
                    scale_x=scale,
                    scale_y=scale,
                    offset_x=source.offset_x,
                    offset_y=source.offset_y,
                )

    @staticmethod
    def _copy_variant(source: FrameVariant, name: str, image: np.ndarray) -> FrameVariant:
        return FrameVariant(
            f"{source.method}-{name}",
            image,
            source.scale_x,
            source.scale_y,
            source.offset_x,
            source.offset_y,
        )

    @staticmethod
    def _center_crop(frame: np.ndarray, crop_ratio: float) -> tuple[np.ndarray, int, int]:
        h, w = frame.shape[:2]
        crop_w = max(1, int(w * crop_ratio))
        crop_h = max(1, int(h * crop_ratio))
        x = (w - crop_w) // 2
        y = (h - crop_h) // 2
        return frame[y : y + crop_h, x : x + crop_w], x, y

    @staticmethod
    def _map_points(points: np.ndarray | None, variant: FrameVariant) -> np.ndarray | None:
        if points is None:
            return None

        mapped = points.astype(np.float32).copy()
        mapped[..., 0] = mapped[..., 0] / variant.scale_x + variant.offset_x
        mapped[..., 1] = mapped[..., 1] / variant.scale_y + variant.offset_y
        return mapped

    @staticmethod
    def digital_zoom(frame: np.ndarray, zoom: float) -> np.ndarray:
        if zoom <= 1.0:
            return frame

        h, w = frame.shape[:2]
        crop_w = max(1, int(w / zoom))
        crop_h = max(1, int(h / zoom))
        x = (w - crop_w) // 2
        y = (h - crop_h) // 2
        cropped = frame[y : y + crop_h, x : x + crop_w]
        return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_CUBIC)

    @staticmethod
    def _gamma(gray: np.ndarray, gamma: float) -> np.ndarray:
        inv_gamma = 1.0 / gamma
        table = np.array(
            [((i / 255.0) ** inv_gamma) * 255 for i in range(256)]
        ).astype("uint8")
        return cv2.LUT(gray, table)

    @staticmethod
    def draw_detection(frame: np.ndarray, points: np.ndarray, method: str) -> None:
        pts = points.astype(int).reshape(-1, 2)
        for i in range(len(pts)):
            cv2.line(frame, tuple(pts[i]), tuple(pts[(i + 1) % len(pts)]), (0, 255, 0), 3)
        cv2.putText(
            frame,
            method,
            (pts[0][0], max(pts[0][1] - 12, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

    @staticmethod
    def estimate_distance_readiness(points: np.ndarray | None, frame: np.ndarray) -> str:
        if points is None:
            return ""

        pts = points.reshape(-1, 2)
        side_lengths = [
            np.linalg.norm(pts[i] - pts[(i + 1) % len(pts)]) for i in range(len(pts))
        ]
        avg_side = float(np.mean(side_lengths))
        frame_short_side = min(frame.shape[:2])
        qr_ratio = avg_side / max(frame_short_side, 1)

        if qr_ratio < 0.08:
            return "QR is very small in frame: use a larger print, move closer, or increase zoom."
        if qr_ratio < 0.14:
            return "QR is readable but small: a larger print improves long-distance reliability."
        return "QR size in frame looks good."


def format_payload(payload: str) -> str:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return payload

    if data.get("vehicle_id"):
        return "\n".join(
            [
                f"Vehicle/Equipment ID: {data.get('vehicle_id', '')}",
                f"Plate Number: {data.get('plate_number', '')}",
                f"Type: {data.get('vehicle_type', '')}",
                f"Owner/Operator: {data.get('owner_operator', '')}",
                f"Site: {data.get('site', '')}",
                f"Route/Checkpoint: {data.get('assigned_route', '')} / {data.get('checkpoint_id', '')}",
                f"Status: {data.get('status', '')}",
            ]
        )

    return "\n".join(
        [
            f"Name: {data.get('name', '')}",
            f"Class: {data.get('class', '')}",
            f"Roll No: {data.get('roll_no', '')}",
            f"Age: {data.get('age', '')}",
            f"Class Teacher: {data.get('class_teacher', '')}",
        ]
    )
