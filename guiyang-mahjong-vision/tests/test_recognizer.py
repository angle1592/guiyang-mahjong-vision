from dataclasses import dataclass

import numpy as np
import pytest

from mahjong_vision.templates import MatchResult


@dataclass
class FakeStore:
    results: list[MatchResult]

    def match(self, image: np.ndarray) -> MatchResult:
        assert image.shape == (1, 1)
        return self.results.pop(0)


def test_unknown_slot_blocks_complete_hand():
    from mahjong_vision.recognizer import HandRecognizer

    store = FakeStore(
        [MatchResult("1m", 0.95, 0.2, True)] * 13
        + [MatchResult("9m", 0.60, 0.59, False)]
    )
    recognizer = HandRecognizer(store)
    slots = [np.zeros((1, 1), dtype=np.uint8) for _ in range(14)]

    result = recognizer.recognize(slots)

    assert not result.complete
    assert result.unknown_slots == (13,)


def test_two_matching_frames_become_stable():
    from mahjong_vision.recognizer import StableHand

    hand = tuple("1m" for _ in range(14))
    stable = StableHand(required_frames=2)

    assert stable.update(hand) is None
    assert stable.update(hand) == hand
