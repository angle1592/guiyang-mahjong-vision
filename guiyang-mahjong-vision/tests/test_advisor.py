import pytest

from mahjong_vision.advisor import AdvisorWeights, advise


WEIGHTS = AdvisorWeights(2.0, 2.5, 0.4)


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

    result = advise(hand, WEIGHTS)

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

    result = advise(hand, WEIGHTS)

    assert result.discard == "1s"


def test_visible_counts_none_matches_omitted_argument():
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

    assert advise(hand, WEIGHTS, None) == advise(hand, WEIGHTS)


def test_discarded_tile_is_not_counted_as_an_effective_draw():
    hand = (
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
        "1s",
        "9s",
    )

    result = advise(hand, WEIGHTS)
    one_man = next(
        alternative for alternative in result.alternatives if alternative.discard == "1m"
    )

    assert one_man.effective_tiles == 16


def test_visible_counts_are_removed_from_effective_draws():
    hand = (
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
        "1s",
        "9s",
    )

    result = advise(hand, WEIGHTS, {"1s": 3})
    dead_wait = next(
        alternative for alternative in result.alternatives if alternative.discard == "9s"
    )

    assert result.discard == "1s"
    assert dead_wait.effective_tiles == 0


def test_sequence_visible_counts_are_supported():
    hand = (
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
        "1s",
        "9s",
    )
    visible_counts = [0] * 27
    visible_counts[18] = 3

    result = advise(hand, WEIGHTS, visible_counts)
    dead_wait = next(
        alternative for alternative in result.alternatives if alternative.discard == "9s"
    )

    assert result.discard == "1s"
    assert dead_wait.effective_tiles == 0


def test_sequence_visible_counts_length_is_validated():
    hand = (
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
        "1s",
        "9s",
    )

    with pytest.raises(ValueError, match="visible_counts must contain 27"):
        advise(hand, WEIGHTS, [0] * 26)


def test_sequence_visible_counts_type_is_validated():
    hand = (
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
        "1s",
        "9s",
    )

    with pytest.raises(ValueError, match="mapping or a sequence"):
        advise(hand, WEIGHTS, object())

    with pytest.raises(ValueError, match="mapping or a sequence"):
        advise(hand, WEIGHTS, "0" * 27)

    visible_counts = [0] * 27
    visible_counts[0] = 1.5
    with pytest.raises(ValueError, match="visible count at index 0"):
        advise(hand, WEIGHTS, visible_counts)


def test_sequence_visible_counts_value_range_is_validated():
    hand = (
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
        "1s",
        "9s",
    )

    visible_counts = [0] * 27
    visible_counts[0] = 5
    with pytest.raises(ValueError, match="visible count at index 0"):
        advise(hand, WEIGHTS, visible_counts)


def test_visible_counts_reject_impossible_known_tile_totals():
    hand = (
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
        "1s",
        "9s",
    )

    with pytest.raises(ValueError, match="too many known copies of 1s"):
        advise(hand, WEIGHTS, {"1s": 4})


def test_thirteen_tile_path_uses_visible_counts():
    hand = (
        "4m",
        "5m",
        "6m",
        "4s",
        "5s",
        "6s",
        "7s",
        "8s",
        "2p",
        "4p",
        "6p",
        "8p",
        "8p",
    )

    result = advise(hand, WEIGHTS, {"3p": 4})

    assert result.discard
    assert result.alternatives
    assert "摸三筒" not in result.reason
    assert "摸" in result.reason


def test_thirteen_tile_hand_still_gets_a_draw_based_suggestion():
    hand = (
        "4m",
        "5m",
        "6m",
        "4s",
        "5s",
        "6s",
        "7s",
        "8s",
        "2p",
        "4p",
        "6p",
        "8p",
        "8p",
    )

    result = advise(hand, WEIGHTS)

    assert result.discard
    assert result.alternatives
    assert "摸" in result.reason


def test_eight_concealed_tiles_after_two_melds_gets_discard_advice():
    hand = (
        "6m",
        "6m",
        "7m",
        "8m",
        "1p",
        "3p",
        "3p",
        "1s",
    )

    result = advise(hand, WEIGHTS)

    assert result.discard in hand
    assert "副露2组" in result.reason


def test_impossible_concealed_tile_counts_are_rejected():
    with pytest.raises(ValueError, match="legal concealed hand size"):
        advise(("1m", "2m", "3m"), WEIGHTS)
