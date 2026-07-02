from __future__ import annotations

import argparse
from pathlib import Path

from mahjong_vision.capture import WindowCapture
from mahjong_vision.config import load_config
from mahjong_vision.templates import TemplateStore
from mahjong_vision.visible_debug import write_visible_debug_capture


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(
        description="Save cropped visible-tile slots and match diagnostics."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=root / "config.json",
        help="Path to config.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "debug" / "visible",
        help="Directory for cropped slots and visible-report.json.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = project_root()
    config = load_config(args.config)
    store = TemplateStore(
        root / "templates",
        size=(48, 72),
        threshold=config.matching.threshold,
        min_margin=config.matching.min_margin,
    )

    with WindowCapture(config.window_title) as capture:
        frame = capture.capture()

    report_path = write_visible_debug_capture(
        frame=frame,
        regions=config.visible_regions,
        store=store,
        output_dir=args.output,
    )
    print(f"Wrote visible region debug report: {report_path}")


if __name__ == "__main__":
    main()
