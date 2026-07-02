from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

import cv2
import numpy as np

from mahjong_vision.config import VisibleRegionConfig, VisibleRegionsConfig
from mahjong_vision.templates import MatchResult
from mahjong_vision.visible_recognizer import Matcher, crop_region_slots


@dataclass(frozen=True)
class VisibleDebugEntry:
    region: int
    slot: int
    image: str
    label: str | None
    accepted: bool
    score: float
    runner_up_score: float


def _write_image(path: Path, image: np.ndarray) -> None:
    if not cv2.imwrite(str(path), image):
        raise OSError(f"failed to write image: {path}")


def _entry(
    *,
    region_index: int,
    slot_index: int,
    image_name: str,
    match: MatchResult,
) -> VisibleDebugEntry:
    return VisibleDebugEntry(
        region=region_index,
        slot=slot_index,
        image=image_name,
        label=match.label,
        accepted=bool(match.accepted),
        score=float(match.score),
        runner_up_score=float(match.runner_up_score),
    )


def _debug_regions(
    *,
    frame: np.ndarray,
    regions: tuple[VisibleRegionConfig, ...],
    source: str,
    store: Matcher,
    output_dir: Path,
) -> list[VisibleDebugEntry]:
    entries: list[VisibleDebugEntry] = []
    for region_index, region in enumerate(regions):
        for slot_index, slot_image in enumerate(crop_region_slots(frame, region)):
            match = store.match(slot_image)
            image_name = f"{source}_{region_index}_slot_{slot_index:02d}.png"
            _write_image(output_dir / image_name, slot_image)
            entries.append(
                _entry(
                    region_index=region_index,
                    slot_index=slot_index,
                    image_name=image_name,
                    match=match,
                )
            )
    return entries


def write_visible_debug_capture(
    *,
    frame: np.ndarray,
    regions: VisibleRegionsConfig,
    store: Matcher,
    output_dir: str | Path,
) -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    frame_name = "frame.png"
    _write_image(output / frame_name, frame)

    report = {
        "frame": frame_name,
        "discards": [
            asdict(entry)
            for entry in _debug_regions(
                frame=frame,
                regions=regions.discards,
                source="discards",
                store=store,
                output_dir=output,
            )
        ],
        "melds": [
            asdict(entry)
            for entry in _debug_regions(
                frame=frame,
                regions=regions.melds,
                source="melds",
                store=store,
                output_dir=output,
            )
        ],
        "revealed": [
            asdict(entry)
            for entry in _debug_regions(
                frame=frame,
                regions=regions.revealed,
                source="revealed",
                store=store,
                output_dir=output,
            )
        ],
    }
    entries = [
        *report["discards"],
        *report["melds"],
        *report["revealed"],
    ]
    report["summary"] = {
        "total_slots": len(entries),
        "accepted_slots": sum(1 for entry in entries if entry["accepted"]),
    }

    report_path = output / "visible-report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report_path
