from __future__ import annotations

from typing import Protocol

import numpy as np

from mahjong_vision.config import Rect, VisibleRegionConfig, VisibleRegionsConfig
from mahjong_vision.templates import MatchResult
from mahjong_vision.visible import VisibleTiles


class Matcher(Protocol):
    def match(self, image: np.ndarray) -> MatchResult: ...


def crop_rect(frame: np.ndarray, rect: Rect) -> np.ndarray:
    if not isinstance(frame, np.ndarray) or frame.size == 0:
        raise ValueError("frame must be a non-empty numpy array")

    frame_height, frame_width = frame.shape[:2]
    right = rect.x + rect.width
    bottom = rect.y + rect.height
    if rect.x < 0 or rect.y < 0 or right > frame_width or bottom > frame_height:
        raise ValueError("visible tile slot is outside the frame")
    return frame[rect.y:bottom, rect.x:right].copy()


def crop_region_slots(
    frame: np.ndarray,
    region: VisibleRegionConfig,
) -> tuple[np.ndarray, ...]:
    return tuple(crop_rect(frame, rect) for rect in region.slot_rects())


class VisibleTileRecognizer:
    def __init__(self, store: Matcher) -> None:
        self.store = store

    def _recognize_region(
        self,
        frame: np.ndarray,
        region: VisibleRegionConfig,
    ) -> tuple[str, ...]:
        labels: list[str] = []
        for slot in crop_region_slots(frame, region):
            match = self.store.match(slot)
            if match.accepted and match.label:
                labels.append(match.label)
        return tuple(labels)

    def recognize(
        self,
        frame: np.ndarray,
        regions: VisibleRegionsConfig,
    ) -> VisibleTiles:
        discards = tuple(
            label
            for region in regions.discards
            for label in self._recognize_region(frame, region)
        )
        melds = []
        for region in regions.melds:
            labels = self._recognize_region(frame, region)
            if len(labels) == region.count:
                melds.append(labels)
        revealed = tuple(
            label
            for region in regions.revealed
            for label in self._recognize_region(frame, region)
        )
        return VisibleTiles(diskards=discards, melds=tuple(melds), revealed=revealed)
