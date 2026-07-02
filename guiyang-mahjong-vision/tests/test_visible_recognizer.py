from dataclasses import dataclass

import numpy as np
import pytest

from mahjong_vision.config import VisibleRegionConfig, VisibleRegionsConfig
from mahjong_vision.domain import Tile
from mahjong_vision.templates import MatchResult
from mahjong_vision.visible_recognizer import (
    VisibleTileRecognizer,
    crop_region_slots,
)


@dataclass
class FakeStore:
    results: list[MatchResult]

    def match(self, image: np.ndarray) -> MatchResult:
        assert image.size
        return self.results.pop(0)


def region(x=0, y=0, count=1) -> VisibleRegionConfig:
    return VisibleRegionConfig(
        x=x,
        y=y,
        slot_width=4,
        slot_height=5,
        stride=6,
        count=count,
    )


def count_for(counts, label):
    return counts[Tile.from_label(label).index]


def accepted(label: str) -> MatchResult:
    return MatchResult(label=label, score=0.95, runner_up_score=0.1, accepted=True)


def rejected() -> MatchResult:
    return MatchResult(label=None, score=0.4, runner_up_score=0.39, accepted=False)


def test_crop_region_slots_uses_configured_slot_geometry():
    frame = np.arange(12 * 20, dtype=np.uint8).reshape(12, 20)

    slots = crop_region_slots(frame, region(x=2, y=3, count=3))

    assert len(slots) == 3
    assert slots[0].shape == (5, 4)
    assert slots[0][0, 0] == frame[3, 2]
    assert slots[1][0, 0] == frame[3, 8]
    assert slots[2][0, 0] == frame[3, 14]


def test_crop_region_slots_rejects_regions_outside_the_frame():
    frame = np.zeros((8, 8, 3), dtype=np.uint8)

    with pytest.raises(ValueError, match="outside the frame"):
        crop_region_slots(frame, region(x=6, y=0, count=1))


def test_visible_tile_recognizer_builds_visible_tiles_from_regions():
    frame = np.zeros((30, 40, 3), dtype=np.uint8)
    regions = VisibleRegionsConfig(
        discards=(region(count=2),),
        melds=(region(y=6, count=3),),
        revealed=(region(y=12, count=1),),
    )
    store = FakeStore(
        [
            accepted("1m"),
            accepted("2m"),
            accepted("3p"),
            accepted("3p"),
            accepted("3p"),
            accepted("8s"),
        ]
    )

    visible = VisibleTileRecognizer(store).recognize(frame, regions)
    counts = visible.to_counts()

    assert visible.discards == ("1m", "2m")
    assert visible.melds == (("3p", "3p", "3p"),)
    assert visible.revealed == ("8s",)
    assert count_for(counts, "1m") == 1
    assert count_for(counts, "2m") == 1
    assert count_for(counts, "3p") == 3
    assert count_for(counts, "8s") == 1


def test_visible_tile_recognizer_ignores_rejected_flat_slots():
    frame = np.zeros((10, 20, 3), dtype=np.uint8)
    regions = VisibleRegionsConfig(
        discards=(region(count=2),),
        melds=(),
        revealed=(),
    )
    store = FakeStore([accepted("1m"), rejected()])

    visible = VisibleTileRecognizer(store).recognize(frame, regions)

    assert visible.discards == ("1m",)


def test_visible_tile_recognizer_skips_incomplete_melds():
    frame = np.zeros((10, 24, 3), dtype=np.uint8)
    regions = VisibleRegionsConfig(
        discards=(),
        melds=(region(count=3),),
        revealed=(),
    )
    store = FakeStore([accepted("4s"), rejected(), accepted("6s")])

    visible = VisibleTileRecognizer(store).recognize(frame, regions)

    assert visible.melds == ()
    assert visible.to_counts() == [0] * 27
