from __future__ import annotations

from mining_qr_scanner import opencv_environment


def test_preview_fix_hint_mentions_headless_when_headless_package_is_installed(monkeypatch) -> None:
    monkeypatch.setattr(
        opencv_environment,
        "installed_opencv_packages",
        lambda: {"opencv-python-headless": "4.13.0"},
    )

    assert "opencv-python-headless" in opencv_environment.preview_fix_hint()


def test_has_preview_support_rejects_none_backend(monkeypatch) -> None:
    monkeypatch.setattr(opencv_environment, "opencv_gui_backend", lambda: "NONE")

    assert opencv_environment.has_preview_support() is False


def test_environment_report_contains_preview_fields(monkeypatch) -> None:
    monkeypatch.setattr(opencv_environment, "opencv_gui_backend", lambda: "Win32 UI")
    monkeypatch.setattr(
        opencv_environment,
        "installed_opencv_packages",
        lambda: {"opencv-python": "4.13.0"},
    )

    report = opencv_environment.environment_report()

    assert report["preview_supported"] is True
    assert report["preview_fix_hint"] == ""
