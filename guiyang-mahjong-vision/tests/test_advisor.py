import pytest

from mahjong_vision.advisor import AdvisorWeights, advise


def test_isolated_nine_is_discarded_from_pair_rich_hand():
    hand = (
        "5m",
        "6m",
        "6m",
        "9m",
        "2s",
        "2s",
        "3s",
        "8s",
        "1p",
        "1p",
        "1p",
        "6p",
        "6p",
        "8s",
    )

    result = advise(hand, AdvisorWeights(2.0, 2.5, 0.4))

    assert result.discard == "9m"
    assert result.shanten_after <= result.alternatives[-1].shanten_after


def test_chicken_weight_does_not_preserve_tile_at_cost_of_shanten():
    hand = (
        "1s",
        "1m",
        "2m",
        "3m",
        "4m",
        "5m",
        "6m",
        "2p",
        "3p",
        "4p",
        "6p",
        "7p",
        "8p",
        "9p",
    )

    result = advise(hand, AdvisorWeights(2.0, 2.5, 0.4))

    assert result.discard == "1s"


def test_fourteen_tiles_are_required():
    with pytest.raises(ValueError, match="14"):
        advise(("1m",), AdvisorWeights(2.0, 2.5, 0.4))
