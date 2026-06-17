from __future__ import annotations

import json
from typing import Iterable

import cv2
import numpy as np


class LightingAdaptiveQRScanner:
    """QR scanner that retries decoding with lighting-aware frame variants."""

    def __init__(self) -> None:
        self.detector = cv2.QRCodeDetector()

    def detect(self, frame: np.ndarray) -> tuple[str, np.ndarray | None, str] | None:
        for method, candidate in self._variants(frame):
            payload, points, _ = self.detector.detectAndDecode(candidate)
            if payload:
                return payload, points, method
        return None

    def _variants(self, frame: np.ndarray) -> Iterable[tuple[str, np.ndarray]]:
        yield "original", frame

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        yield "grayscale", gray

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast = clahe.apply(gray)
        yield "contrast-normalized", contrast

        for gamma in (0.6, 0.8, 1.3, 1.7):
            yield f"gamma-{gamma}", self._gamma(gray, gamma)

        blurred = cv2.GaussianBlur(contrast, (0, 0), 1.2)
        sharpened = cv2.addWeighted(contrast, 1.6, blurred, -0.6, 0)
        yield "sharpened", sharpened

        adaptive = cv2.adaptiveThreshold(
            contrast,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            4,
        )
        yield "adaptive-threshold", adaptive

        h, w = gray.shape[:2]
        if max(h, w) < 1400:
            upscaled = cv2.resize(
                contrast, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC
            )
            yield "upscaled-contrast", upscaled

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


def format_payload(payload: str) -> str:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return payload

    return "\n".join(
        [
            f"Name: {data.get('name', '')}",
            f"Class: {data.get('class', '')}",
            f"Roll No: {data.get('roll_no', '')}",
            f"Age: {data.get('age', '')}",
            f"Class Teacher: {data.get('class_teacher', '')}",
        ]
    )
