from __future__ import annotations

from importlib import metadata

import cv2


def installed_opencv_packages() -> dict[str, str]:
    packages = {}
    for package_name in ("opencv-python", "opencv-contrib-python", "opencv-python-headless"):
        try:
            packages[package_name] = metadata.version(package_name)
        except metadata.PackageNotFoundError:
            continue
    return packages


def opencv_gui_backend() -> str:
    build_info = cv2.getBuildInformation()
    for line in build_info.splitlines():
        stripped = line.strip()
        if stripped.startswith("GUI:"):
            return stripped.split(":", 1)[1].strip()
    return "unknown"


def has_preview_support() -> bool:
    backend = opencv_gui_backend().casefold()
    return bool(backend and backend not in {"none", "no", "unknown"})


def preview_fix_hint() -> str:
    packages = installed_opencv_packages()
    if "opencv-python-headless" in packages:
        return (
            "Preview windows need a GUI-enabled OpenCV build. Run: "
            "python -m pip uninstall opencv-python-headless -y; "
            "python -m pip install --upgrade opencv-python"
        )
    if "opencv-python" not in packages and "opencv-contrib-python" not in packages:
        return "Install OpenCV with preview support: python -m pip install opencv-python"
    return (
        "OpenCV is installed, but this build does not expose preview windows. "
        "Try: python -m pip install --upgrade --force-reinstall opencv-python"
    )


def environment_report() -> dict:
    return {
        "cv2_version": cv2.__version__,
        "installed_packages": installed_opencv_packages(),
        "gui_backend": opencv_gui_backend(),
        "preview_supported": has_preview_support(),
        "preview_fix_hint": "" if has_preview_support() else preview_fix_hint(),
    }
