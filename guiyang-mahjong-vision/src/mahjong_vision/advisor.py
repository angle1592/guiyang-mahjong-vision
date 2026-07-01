from __future__ import annotations

from dataclasses import dataclass

from mahjong_vision.domain import Tile


@dataclass(frozen=True)
class AdvisorWeights:
    one_bamboo: float
    eight_dot: float
    pair: float


@dataclass(frozen=True)
class Alternative:
    discard: str
    shanten_after: int
    effective_tiles: int
    keep_value: float


@dataclass(frozen=True)
class Advice:
    discard: str
    reason: str
    shanten_after: int
    alternatives: tuple[Alternative, ...]


def _standard_shanten(counts: list[int]) -> int:
    best = 8

    def walk(index: int, melds: int, pairs: int, taatsu: int) -> None:
        nonlocal best
        while index < 27 and counts[index] == 0:
            index += 1
        if index == 27:
            usable_taatsu = min(taatsu, 4 - melds)
            best = min(best, 8 - 2 * melds - usable_taatsu - min(pairs, 1))
            return

        walk(index + 1, melds, pairs, taatsu)

        if counts[index] >= 3:
            counts[index] -= 3
            walk(index, melds + 1, pairs, taatsu)
            counts[index] += 3

        suit_position = index % 9
        if suit_position <= 6 and counts[index + 1] and counts[index + 2]:
            counts[index] -= 1
            counts[index + 1] -= 1
            counts[index + 2] -= 1
            walk(index, melds + 1, pairs, taatsu)
            counts[index] += 1
            counts[index + 1] += 1
            counts[index + 2] += 1

        if counts[index] >= 2:
            counts[index] -= 2
            walk(index, melds, pairs + 1, taatsu)
            walk(index, melds, pairs, taatsu + 1)
            counts[index] += 2

        if suit_position <= 7 and counts[index + 1]:
            counts[index] -= 1
            counts[index + 1] -= 1
            walk(index, melds, pairs, taatsu + 1)
            counts[index] += 1
            counts[index + 1] += 1

        if suit_position <= 6 and counts[index + 2]:
            counts[index] -= 1
            counts[index + 2] -= 1
            walk(index, melds, pairs, taatsu + 1)
            counts[index] += 1
            counts[index + 2] += 1

    walk(0, 0, 0, 0)
    return best


def _seven_pairs_shanten(counts: list[int]) -> int:
    pair_types = sum(count >= 2 for count in counts)
    distinct = sum(count > 0 for count in counts)
    return 6 - pair_types + max(0, 7 - distinct)


def _shanten(counts: list[int]) -> int:
    return min(_standard_shanten(counts.copy()), _seven_pairs_shanten(counts))


def _effective_draws(counts: list[int], base_shanten: int) -> int:
    total = 0
    for draw_index, count in enumerate(counts):
        if count >= 4:
            continue
        counts[draw_index] += 1
        if _shanten(counts) < base_shanten:
            total += 4 - count
        counts[draw_index] -= 1
    return total


def _keep_value(tile: Tile, original_count: int, weights: AdvisorWeights) -> float:
    value = weights.pair if original_count >= 2 else 0.0
    if tile.label == "1s":
        value += weights.one_bamboo
    if tile.label == "8p":
        value += weights.eight_dot
    return value


def _discard_structure_cost(tile_index: int, counts: list[int]) -> int:
    if counts[tile_index] >= 2:
        return 2

    suit_position = tile_index % 9
    connected = False
    for offset in (-2, -1, 1, 2):
        neighbor_position = suit_position + offset
        if not 0 <= neighbor_position <= 8:
            continue
        if counts[tile_index + offset]:
            connected = True
            break
    return 1 if connected else 0


def advise(labels: tuple[str, ...], weights: AdvisorWeights) -> Advice:
    if len(labels) != 14:
        raise ValueError("advisor requires exactly 14 tiles")

    counts = [0] * 27
    for label in labels:
        tile = Tile.from_label(label)
        counts[tile.index] += 1
        if counts[tile.index] > 4:
            raise ValueError(f"too many copies of {label}")

    alternatives: list[Alternative] = []
    original_counts = counts.copy()
    for tile_index, original_count in enumerate(counts):
        if not original_count:
            continue
        tile = Tile(tile_index)
        counts[tile_index] -= 1
        shanten_after = _shanten(counts)
        effective_tiles = _effective_draws(counts, shanten_after)
        counts[tile_index] += 1
        alternatives.append(
            Alternative(
                discard=tile.label,
                shanten_after=shanten_after,
                effective_tiles=effective_tiles,
                keep_value=_keep_value(tile, original_count, weights),
            )
        )

    alternatives.sort(
        key=lambda alternative: (
            alternative.shanten_after,
            _discard_structure_cost(
                Tile.from_label(alternative.discard).index,
                original_counts,
            ),
            -alternative.effective_tiles,
            alternative.keep_value,
            Tile.from_label(alternative.discard).index,
        )
    )
    best = alternatives[0]
    display_name = Tile.from_label(best.discard).display_name
    reason = (
        f"打{display_name}："
        f"向听数{best.shanten_after}，有效进张{best.effective_tiles}张"
    )
    return Advice(
        discard=best.discard,
        reason=reason,
        shanten_after=best.shanten_after,
        alternatives=tuple(alternatives),
    )
