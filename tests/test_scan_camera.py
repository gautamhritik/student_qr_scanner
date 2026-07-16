from __future__ import annotations

from types import SimpleNamespace

import pytest

import scan_camera


def valid_args(**overrides):
    args = {
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "digital_zoom": 1.0,
        "scan_cooldown": 3.0,
        "preview_scale": 1.0,
        "max_scans": None,
        "no_preview": False,
        "vote_window": 5,
        "min_votes": 3,
        "site_id": "mine-1",
        "gate_id": "main-gate",
        "camera_id": "pole-cam-1",
        "checkpoint_id": "gate-1",
        "direction": "in",
    }
    args.update(overrides)
    return SimpleNamespace(**args)


def test_parse_camera_keeps_urls_and_converts_indexes() -> None:
    assert scan_camera.parse_camera("0") == 0
    assert scan_camera.parse_camera("2") == 2
    assert scan_camera.parse_camera("http://127.0.0.1:8080/video") == (
        "http://127.0.0.1:8080/video"
    )


@pytest.mark.parametrize(
    "override",
    [
        {"width": 0},
        {"height": 0},
        {"fps": 0},
        {"digital_zoom": 0.9},
        {"scan_cooldown": -1},
        {"preview_scale": 0},
        {"max_scans": 0},
        {"vote_window": 0},
        {"min_votes": 0},
        {"vote_window": 2, "min_votes": 3},
        {"site_id": ""},
        {"gate_id": ""},
        {"camera_id": ""},
        {"checkpoint_id": ""},
    ],
)
def test_validate_args_rejects_invalid_values(override) -> None:
    with pytest.raises(SystemExit):
        scan_camera.validate_args(valid_args(**override))


def test_validate_args_accepts_valid_values() -> None:
    scan_camera.validate_args(valid_args(max_scans=5, preview_scale=0.5))


def test_parser_defaults_allow_plain_scanner_command() -> None:
    parser = scan_camera.build_parser()

    args = parser.parse_args([])

    assert args.direction == "in"
    assert args.site_id == "mine-1"
    assert args.gate_id == "main-gate"


def test_expected_backends_are_available() -> None:
    assert {"auto", "any", "dshow", "msmf", "v4l2"} <= set(scan_camera.BACKENDS)


def test_accepted_payload_from_votes_waits_for_majority() -> None:
    recent = scan_camera.deque(maxlen=3)

    assert scan_camera.accepted_payload_from_votes(recent, "A", 3, 2) is None
    assert scan_camera.accepted_payload_from_votes(recent, "B", 3, 2) is None
    assert scan_camera.accepted_payload_from_votes(recent, "A", 3, 2) == "A"


def test_accepted_payload_from_votes_does_not_accept_stale_majority() -> None:
    recent = scan_camera.deque(["A", "A"], maxlen=3)

    assert scan_camera.accepted_payload_from_votes(recent, "B", 3, 2) is None


def test_accepted_payload_from_votes_accepts_immediately_when_disabled() -> None:
    recent = scan_camera.deque(maxlen=1)

    assert scan_camera.accepted_payload_from_votes(recent, "A", 1, 1) == "A"


def test_open_camera_forwards_backend_to_opencv(monkeypatch) -> None:
    calls = []

    def fake_video_capture(*args):
        calls.append(args)
        return object()

    monkeypatch.setattr(scan_camera.cv2, "VideoCapture", fake_video_capture)

    scan_camera.open_camera(0, "auto")
    scan_camera.open_camera(1, "dshow")

    assert calls[0] == (0,)
    assert calls[1] == (1, scan_camera.BACKENDS["dshow"])


def test_show_preview_returns_false_when_imshow_fails(monkeypatch) -> None:
    def fake_imshow(*args):
        raise scan_camera.cv2.error("preview unavailable")

    monkeypatch.setattr(scan_camera.cv2, "imshow", fake_imshow)

    assert scan_camera.show_preview("window", object(), 1.0) is False


def test_preview_unavailable_message_includes_repair_hint(monkeypatch) -> None:
    monkeypatch.setattr(scan_camera, "preview_fix_hint", lambda: "repair command")

    message = scan_camera.preview_unavailable_message()

    assert "terminal-only mode" in message
    assert "repair command" in message


def test_show_preview_scales_frame(monkeypatch):
    calls = []

    def fake_resize(frame, *args, **kwargs):
        calls.append(("resize", args, kwargs))
        return "resized"

    def fake_imshow(window_name, frame):
        calls.append(("imshow", window_name, frame))

    monkeypatch.setattr(scan_camera.cv2, "resize", fake_resize)
    monkeypatch.setattr(scan_camera.cv2, "imshow", fake_imshow)

    assert scan_camera.show_preview("window", object(), 0.5) is True
    assert calls[0][0] == "resize"
    assert calls[1] == ("imshow", "window", "resized")
