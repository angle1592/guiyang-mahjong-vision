import pytest

from mahjong_vision.domain import Tile
from mahjong_vision.visible import VisibleTiles, to_visible_counts


def count_for(counts, label):
    return counts[Tile.from_label(label).index]


def test_visible_tiles_counts_discards_melds_and_revealed_tiles():
    visible = VisibleTiles(
        discards=("1m", "2m", "1s"),
        melds=(("3p", "3p", "3p"), ("4s", "5s", "6s")),
        revealed=("8p",),
    )

    counts = visible.to_counts()

    assert count_for(counts, "1m") == 1
    assert count_for(counts, "2m") == 1
    assert count_for(counts, "3p") == 3
    assert count_for(counts, "8p") == 1
    assert count_for(counts, "1s") == 1
    assert count_for(counts, "4s") == 1
    assert count_for(counts, "5s") == 1
    assert count_for(counts, "6s") == 1
    assert sum(counts) == 10


def test_visible_tiles_normalizes_generators_to_immutable_tuples():
    discards = (label for label in ("1m", "2m"))
    melds = (["3p", "3p", "3p"],)

    visible = VisibleTiles(discards=discards, melds=melds)

    assert visible.discards == ("1m", "2m")
    assert visible.melds == (("3p", "3p", "3p"),)
    assert visible.labels() == ("1m", "2m", "3p", "3p", "3p")


def test_to_visible_counts_returns_a_fresh_mutable_advisor_count_list():
    visible = VisibleTiles(discards=("1m",))

    first = to_visible_counts(visible)
    second = to_visible_counts(visible)
    first[Tile.from_label("1m").index] = 0

    assert count_for(second, "1m") == 1


def test_visible_tiles_rejects_invalid_tile_labels():
    with pytest.raises(ValueError, match="tile label"):
        VisibleTiles(discards=("10m",))

    with pytest.raises(ValueError, match="tile label"):
        VisibleTiles(melds=(("1m", "east"),))


def test_visible_tiles_rejects_string_sources():
    with pytest.raises(ValueError, match="discards"):
        VisibleTiles(discards="1m")

    with pytest.raises(ValueError, match="melds"):
        VisibleTiles(melds="1m")

    with pytest.raises(ValueError, match=r"melds\[0\]"):
        VisibleTiles(melds=("1m",))


def test_visible_tiles_rejects_more_than_four_visible_copies():
    visible = VisibleTiles(
        discards=("1m", "1m"),
        melds=(("1m", "1m", "1m"),),
    )

    with pytest.raises(ValueError, match="too many visible copies of 1m"):
        visible.to_counts()
