import json
from pathlib import Path
from typing import Any

import pytest

from mahjong_vision.config import load_config


PROJECT_ROOT = Path(__file__).parents[1]


def write_config(tmp_path: Path, updates: dict[tuple[str, ...], Any]) -> Path:
    raw_config = json.loads((PROJECT_ROOT / "config.json").read_text(encoding="utf-8"))
    if "title" in raw_config:
        raw_config["window_title"] = raw_config.pop("title")
    for path, value in updates.items():
        target = raw_config
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(raw_config), encoding="utf-8")
    return config_path


def test_load_config_builds_fourteen_hand_slots() -> None:
    config = load_config(PROJECT_ROOT / "config.json")

    slots = config.hand.slot_rects()

    assert config.window_title == "多乐贵阳捉鸡麻将"
    assert len(slots) == 14
    assert slots[-1].x == config.hand.x + 13 * config.hand.stride


def test_load_config_rejects_non_fourteen_tile_hand(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="14"):
        load_config(write_config(tmp_path, {("hand", "count"): 13}))


@pytest.mark.parametrize("threshold", [0, 1])
def test_load_config_accepts_matching_threshold_endpoints(
    tmp_path: Path, threshold: int
) -> None:
    config = load_config(
        write_config(tmp_path, {("matching", "threshold"): threshold})
    )

    assert config.matching.threshold == threshold


def test_load_config_accepts_zero_hand_coordinates(tmp_path: Path) -> None:
    config = load_config(
        write_config(tmp_path, {("hand", "x"): 0, ("hand", "y"): 0})
    )

    assert config.hand.x == 0
    assert config.hand.y == 0


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("window_title",), ""),
        (("window_title",), 123),
        (("hand", "x"), -1),
        (("hand", "x"), True),
        (("hand", "y"), 1.5),
        (("hand", "slot_width"), 0),
        (("hand", "slot_height"), -1),
        (("hand", "stride"), "62"),
        (("hand", "count"), 14.0),
        (("hand", "count"), True),
        (("matching", "threshold"), -0.01),
        (("matching", "threshold"), 1.01),
        (("matching", "threshold"), False),
        (("matching", "min_margin"), -0.01),
        (("matching", "min_margin"), 1.01),
        (("matching", "min_margin"), True),
        (("runtime", "fps"), 0),
        (("runtime", "fps"), 20.0),
        (("runtime", "fps"), True),
        (("runtime", "stable_frames"), -1),
        (("runtime", "stable_frames"), 2.0),
        (("runtime", "stable_frames"), False),
        (("advisor", "one_bamboo_weight"), True),
        (("advisor", "eight_dot_weight"), "2.5"),
        (("advisor", "pair_weight"), False),
    ],
)
def test_load_config_rejects_invalid_values(
    tmp_path: Path, path: tuple[str, ...], value: Any
) -> None:
    with pytest.raises(ValueError):
        load_config(write_config(tmp_path, {path: value}))


@pytest.mark.parametrize(
    "raw_config",
    [
        [],
        {"window_title": "title"},
        {
            "window_title": "title",
            "hand": [],
            "matching": {},
            "runtime": {},
            "advisor": {},
        },
    ],
)
def test_load_config_rejects_invalid_json_shape(
    tmp_path: Path, raw_config: Any
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(raw_config), encoding="utf-8")

    with pytest.raises(ValueError):
        load_config(config_path)
