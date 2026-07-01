from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Protocol

import numpy as np

from mahjong_vision.templates import MatchResult


class Matcher(Protocol):
    def match(self, image: np.ndarray) -> MatchResult: ...


@dataclass(frozen=True)
class Recognition:
    labels: tuple[str | None, ...]
    scores: tuple[float, ...]
    unknown_slots: tuple[int, ...]
    elapsed_ms: float

    @property
    def complete(self) -> bool:
        return len(self.labels) == 14 and not self.unknown_slots


class HandRecognizer:
    def __init__(self, store: Matcher) -> None:
        self.store = store

    def recognize(self, slots: tuple[np.ndarray, ...]) -> Recognition:
        started = perf_counter()
        matches = tuple(self.store.match(slot) for slot in slots)
        unknown_slots = tuple(
            index for index, match in enumerate(matches) if not match.accepted
        )
        labels = tuple(match.label if match.accepted else None for match in matches)
        return Recognition(
            labels=labels,
            scores=tuple(match.score for match in matches),
            unknown_slots=unknown_slots,
            elapsed_ms=(perf_counter() - started) * 1000,
        )


class StableHand:
    def __init__(self, required_frames: int) -> None:
        self.required_frames = required_frames
        self._last: tuple[str, ...] | None = None
        self._count = 0

    def update(self, hand: tuple[str, ...]) -> tuple[str, ...] | None:
        if hand == self._last:
            self._count += 1
        else:
            self._last = hand
            self._count = 1
        if self._count >= self.required_frames:
            return hand
        return None
