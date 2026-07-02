from types import SimpleNamespace

import numpy as np

from mahjong_vision.app import _visible_counts_for_frame
from mahjong_vision.config import VisibleRegionConfig, VisibleRegionsConfig
from mahjong_vision.visible import VisibleTiles


def configured_with_regions() -> SimpleNamespace:
    return SimpleNamespace(
        visible=VisibleTiles(discards=("9s",)),
        visible_regions=VisibleRegionsConfig(
            discards=(VisibleRegionConfig(0, 0, 2, 2, 2, 1),),
            melds=(),
            revealed=(),
        ),
    )


def test_visible_counts_for_frame_uses_recognized_tiles_when_available():
    recognizer = SimpleNamespace(
        recognize=lambda _frame, _regions: VisibleTiles(discards=("1m", "2m"))
    )

    counts = _visible_counts_for_frame(
        np.zeros((4, 4), dtype=np.uint8),
        configured_with_regions(),
        recognizer,
    )

    assert counts[0] == 1
    assert counts[1] == 1
    assert counts[26] == 0


def test_visible_counts_for_frame_falls_back_to_configured_tiles_on_failure():
    def fail(_frame, _regions):
        raise ValueError("region outside frame")

    recognizer = SimpleNamespace(recognize=fail)

    counts = _visible_counts_for_frame(
        np.zeros((4, 4), dtype=np.uint8),
        configured_with_regions(),
        recognizer,
    )

    assert counts[26] == 1


def test_visible_counts_for_frame_falls_back_when_no_region_is_configured():
    config = SimpleNamespace(
        visible=VisibleTiles(discards=("9s",)),
        visible_regions=VisibleRegionsConfig(discards=(), melds=(), revealed=()),
    )
    recognizer = SimpleNamespace(recognize=lambda *_args: VisibleTiles(discards=("1m",)))

    counts = _visible_counts_for_frame(np.zeros((4, 4), dtype=np.uint8), config, recognizer)

    assert counts[26] == 1
    assert counts[0] == 0
