import json
from pathlib import Path

import pytest

from mahjong_vision.config import load_config


PROJECT_ROOT = Path(__file__).parents[1]


def write_config(tmp_path: Path, visible_regions) -> Path:
    raw_config = json.loads((PROJECT_ROOT / "config.json").read_text(encoding="utf-8"))
    raw_config["visible_regions"] = visible_regions
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(raw_config), encoding="utf-8")
    return config_path


def region(**overrides):
    value = {
        "x": 10,
        "y": 20,
        "slot_width": 30,
        "slot_height": 40,
        "stride": 35,
        "count": 2,
    }
    value.update(overrides)
    return value


def test_load_config_accepts_visible_region_sources(tmp_path: Path) -> None:
    config = load_config(
        write_config(
            tmp_path,
            {
                "discards": [region()],
                "melds": [region(count=3)],
                "revealed": [region(count=1)],
            },
        )
    )

    assert config.visible_regions.has_regions()
    assert config.visible_regions.discards[0].slot_rects()[1].x == 45
    assert config.visible_regions.melds[0].count == 3
    assert config.visible_regions.revealed[0].count == 1


def test_load_config_defaults_missing_visible_regions(tmp_path: Path) -> None:
    raw_config = json.loads((PROJECT_ROOT / "config.json").read_text(encoding="utf-8"))
    raw_config.pop("visible_regions", None)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(raw_config), encoding="utf-8")

    config = load_config(config_path)

    assert not config.visible_regions.has_regions()


@pytest.mark.parametrize(
    "visible_regions",
    [
        "region",
        {"discards": "region"},
        {"discards": [{"x": 0}]},
        {"discards": [region(x=-1)]},
        {"discards": [region(slot_width=0)]},
        {"discards": [region(count=0)]},
        {"discards": [region(stride=True)]},
    ],
)
def test_load_config_rejects_invalid_visible_regions(
    tmp_path: Path,
    visible_regions,
) -> None:
    with pytest.raises(ValueError):
        load_config(write_config(tmp_path, visible_regions))
