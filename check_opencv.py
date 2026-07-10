from __future__ import annotations

import json

from mining_qr_scanner.opencv_environment import environment_report


def main() -> None:
    report = environment_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["preview_supported"]:
        print("OpenCV preview windows are available.")
    else:
        print(report["preview_fix_hint"])


if __name__ == "__main__":
    main()
