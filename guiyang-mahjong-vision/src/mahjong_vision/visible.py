from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from mahjong_vision.domain import Tile


TileLabels = Iterable[str]
MeldLabels = Iterable[TileLabels]


def _normalize_labels(labels: TileLabels, name: str) -> tuple[str, ...]:
    if isinstance(labels, (str, bytes, bytearray)):
        raise ValueError(f"{name} must be an iterable of tile labels")

    normalized: list[str] = []
    for label in labels:
        normalized.append(Tile.from_label(label).label)
    return tuple(normalized)


def _normalize_melds(melds: MeldLabels) -> tuple[tuple[str, ...], ...]:
    if isinstance(melds, (str, bytes, bytearray)):
        raise ValueError("melds must be an iterable of tile-label groups")

    return tuple(
        _normalize_labels(meld, f"melds[{index}]")
        for index, meld in enumerate(melds)
    )


def _add_labels(counts: list[int], labels: tuple[str, ...]) -> None:
    for label in labels:
        tile = Tile.from_label(label)
        counts[tile.index] += 1
        if counts[tile.index] > 4:
            raise ValueError(f"too many visible copies of {tile.label}")


@dataclass(frozen=True)
class VisibleTiles:
    discards: TileLabels = ()
    melds: MeldLabels = ()
    revealed: TileLabels = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "discards",
            _normalize_labels(self.discards, "discards"),
        )
        object.__setattr__(self, "melds", _normalize_melds(self.melds))
        object.__setattr__(
            self,
            "revealed",
            _normalize_labels(self.revealed, "revealed"),
        )

    def labels(self) -> tuple[str, ...]:
        return (
            self.discards
            + tuple(label for meld in self.melds for label in meld)
            + self.revealed
        )

    def to_counts(self) -> list[int]:
        counts = [0] * 27
        _add_labels(counts, self.discards)
        for meld in self.melds:
            _add_labels(counts, meld)
        _add_labels(counts, self.revealed)
        return counts


def to_visible_counts(visible_tiles: VisibleTiles) -> list[int]:
    return visible_tiles.to_counts()
