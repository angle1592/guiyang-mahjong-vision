from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from mahjong_vision.domain import Tile


VisibleCounts = Mapping[str, int] | Sequence[int] | None


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


def _standard_shanten(counts: list[int], fixed_melds: int = 0) -> int:
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

    walk(0, fixed_melds, 0, 0)
    return best


def _seven_pairs_shanten(counts: list[int]) -> int:
    pair_types = sum(count >= 2 for count in counts)
    distinct = sum(count > 0 for count in counts)
    return 6 - pair_types + max(0, 7 - distinct)


def _shanten(counts: list[int], fixed_melds: int = 0) -> int:
    standard = _standard_shanten(counts.copy(), fixed_melds)
    if fixed_melds:
        return standard
    return min(standard, _seven_pairs_shanten(counts))


def _effective_draws(
    counts: list[int],
    visible_counts: list[int],
    base_shanten: int,
    fixed_melds: int,
) -> int:
    total = 0
    for draw_index, count in enumerate(counts):
        remaining = 4 - count - visible_counts[draw_index]
        if remaining <= 0:
            continue
        counts[draw_index] += 1
        if _shanten(counts, fixed_melds) < base_shanten:
            total += remaining
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


def _rank_discards(
    counts: list[int],
    weights: AdvisorWeights,
    fixed_melds: int,
    visible_counts: list[int],
) -> tuple[Alternative, ...]:
    alternatives: list[Alternative] = []
    original_counts = counts.copy()
    for tile_index, original_count in enumerate(counts):
        if not original_count:
            continue
        tile = Tile(tile_index)
        counts[tile_index] -= 1
        shanten_after = _shanten(counts, fixed_melds)
        effective_tiles = _effective_draws(
            counts,
            visible_counts,
            shanten_after,
            fixed_melds,
        )
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
    return tuple(alternatives)


def _validate_tile_count(count: int, name: str) -> int:
    if type(count) is not int or not 0 <= count <= 4:
        raise ValueError(f"{name} must be an integer from 0 to 4")
    return count


def _normalize_visible_counts(visible_counts: VisibleCounts) -> list[int]:
    counts = [0] * 27
    if visible_counts is None:
        return counts

    if isinstance(visible_counts, Mapping):
        for label, count in visible_counts.items():
            tile = Tile.from_label(label)
            counts[tile.index] = _validate_tile_count(
                count,
                f"visible count for {label}",
            )
        return counts

    if len(visible_counts) != 27:
        raise ValueError("visible_counts must contain 27 tile counts")

    return [
        _validate_tile_count(count, f"visible count at index {index}")
        for index, count in enumerate(visible_counts)
    ]


def _validate_known_counts(counts: list[int], visible_counts: list[int]) -> None:
    for index, (hand_count, visible_count) in enumerate(zip(counts, visible_counts)):
        if hand_count + visible_count > 4:
            raise ValueError(f"too many known copies of {Tile(index).label}")


def _counts(labels: tuple[str, ...]) -> list[int]:
    counts = [0] * 27
    for label in labels:
        tile = Tile.from_label(label)
        counts[tile.index] += 1
        if counts[tile.index] > 4:
            raise ValueError(f"too many copies of {label}")
    return counts


def _hand_shape(tile_count: int) -> tuple[int, bool]:
    before_draw = {13: 0, 10: 1, 7: 2, 4: 3, 1: 4}
    after_draw = {14: 0, 11: 1, 8: 2, 5: 3, 2: 4}
    if tile_count in before_draw:
        return before_draw[tile_count], False
    if tile_count in after_draw:
        return after_draw[tile_count], True
    raise ValueError("advisor requires a legal concealed hand size")


def advise(
    labels: tuple[str, ...],
    weights: AdvisorWeights,
    visible_counts: VisibleCounts = None,
) -> Advice:
    fixed_melds, after_draw = _hand_shape(len(labels))

    counts = _counts(labels)
    known_visible_counts = _normalize_visible_counts(visible_counts)
    _validate_known_counts(counts, known_visible_counts)

    if not after_draw:
        best_draw: Tile | None = None
        best_alternative: Alternative | None = None
        best_alternatives: tuple[Alternative, ...] = ()
        best_key: tuple[int, int, float, int] | None = None
        for draw_index, count in enumerate(counts):
            if count + known_visible_counts[draw_index] >= 4:
                continue
            counts[draw_index] += 1
            alternatives = _rank_discards(
                counts,
                weights,
                fixed_melds,
                known_visible_counts,
            )
            counts[draw_index] -= 1
            candidate = alternatives[0]
            key = (
                candidate.shanten_after,
                -candidate.effective_tiles,
                candidate.keep_value,
                draw_index,
            )
            if best_key is None or key < best_key:
                best_key = key
                best_draw = Tile(draw_index)
                best_alternative = candidate
                best_alternatives = alternatives
        if best_draw is None or best_alternative is None:
            raise ValueError("no drawable tiles remain")
        discard_name = Tile.from_label(best_alternative.discard).display_name
        meld_text = f"副露{fixed_melds}组，" if fixed_melds else ""
        reason = (
            f"{meld_text}若摸{best_draw.display_name}，打{discard_name}："
            f"向听数{best_alternative.shanten_after}，"
            f"有效进张{best_alternative.effective_tiles}张"
        )
        return Advice(
            discard=best_alternative.discard,
            reason=reason,
            shanten_after=best_alternative.shanten_after,
            alternatives=best_alternatives,
        )

    alternatives = _rank_discards(
        counts,
        weights,
        fixed_melds,
        known_visible_counts,
    )
    best = alternatives[0]
    display_name = Tile.from_label(best.discard).display_name
    meld_text = f"副露{fixed_melds}组，" if fixed_melds else ""
    reason = (
        f"{meld_text}打{display_name}："
        f"向听数{best.shanten_after}，有效进张{best.effective_tiles}张"
    )
    return Advice(
        discard=best.discard,
        reason=reason,
        shanten_after=best.shanten_after,
        alternatives=alternatives,
    )
