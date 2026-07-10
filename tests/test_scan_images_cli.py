from __future__ import annotations

from pathlib import Path

import scan_images


def test_parser_defaults_direction_to_in_for_image_scans() -> None:
    parser = scan_images.build_parser()

    args = parser.parse_args([str(Path("captures"))])

    assert args.direction == "in"
    assert args.inputs == [Path("captures")]
