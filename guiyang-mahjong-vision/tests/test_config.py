from pathlib import Path
import json

import pytest

from mahjong_vision.config import load_config


PROJECT_ROOT = Path(__file__).parents[1]


def test_load_config_builds_fourteen_hand_slots() -> None:
    config = load_config(PROJECT_ROOT / "config.json")

    slots = config.hand.slot_rects()

    assert len(slots) == 14
    assert slots[-1].x == config.hand.x + 13 * config.hand.stride


def test_load_config_rejects_non_fourteen_tile_hand(tmp_path: Path) -> None:
    raw_config = json.loads((PROJECT_ROOT / "config.json").read_text(encoding="utf-8"))
    raw_config["hand"]["count"] = 13
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(raw_config), encoding="utf-8")

    with pytest.raises(ValueError, match="14"):
        load_config(config_path)
