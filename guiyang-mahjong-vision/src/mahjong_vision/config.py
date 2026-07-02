from dataclasses import dataclass
import json
from pathlib import Path

from mahjong_vision.visible import VisibleTiles


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class HandConfig:
    x: int
    y: int
    slot_width: int
    slot_height: int
    stride: int
    count: int

    def slot_rects(self) -> tuple[Rect, ...]:
        return tuple(
            Rect(
                x=self.x + index * self.stride,
                y=self.y,
                width=self.slot_width,
                height=self.slot_height,
            )
            for index in range(self.count)
        )


@dataclass(frozen=True)
class VisibleRegionConfig:
    x: int
    y: int
    slot_width: int
    slot_height: int
    stride: int
    count: int

    def slot_rects(self) -> tuple[Rect, ...]:
        return tuple(
            Rect(
                x=self.x + index * self.stride,
                y=self.y,
                width=self.slot_width,
                height=self.slot_height,
            )
            for index in range(self.count)
        )


@dataclass(frozen=True)
class VisibleRegionsConfig:
    discards: tuple[VisibleRegionConfig, ...]
    melds: tuple[VisibleRegionConfig, ...]
    revealed: tuple[VisibleRegionConfig, ...]

    def has_regions(self) -> bool:
        return bool(self.discards or self.melds or self.revealed)


@dataclass(frozen=True)
class MatchingConfig:
    threshold: float
    min_margin: float


@dataclass(frozen=True)
class RuntimeConfig:
    fps: int
    stable_frames: int


@dataclass(frozen=True)
class AdvisorConfig:
    one_bamboo_weight: float
    eight_dot_weight: float
    pair_weight: float


@dataclass(frozen=True)
class AppConfig:
    window_title: str
    hand: HandConfig
    matching: MatchingConfig
    runtime: RuntimeConfig
    advisor: AdvisorConfig
    visible: VisibleTiles
    visible_regions: VisibleRegionsConfig


def _object(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a JSON object")
    return value


def _required(data: dict[str, object], key: str, section: str) -> object:
    try:
        return data[key]
    except KeyError as error:
        raise ValueError(f"{section}.{key} is required") from error


def _integer(data: dict[str, object], key: str, section: str) -> int:
    value = _required(data, key, section)
    if type(value) is not int:
        raise ValueError(f"{section}.{key} must be an integer")
    return value


def _number(data: dict[str, object], key: str, section: str) -> int | float:
    value = _required(data, key, section)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{section}.{key} must be numeric")
    return value


def _optional_array(data: dict[str, object], key: str, section: str) -> tuple[object, ...]:
    value = data.get(key, [])
    if not isinstance(value, list):
        raise ValueError(f"{section}.{key} must be a JSON array")
    return tuple(value)


def _visible_tiles(raw: dict[str, object]) -> VisibleTiles:
    visible_raw = raw.get("visible", {})
    visible = _object(visible_raw, "visible")
    discards = _optional_array(visible, "discards", "visible")
    revealed = _optional_array(visible, "revealed", "visible")
    melds = _optional_array(visible, "melds", "visible")
    for index, meld in enumerate(melds):
        if not isinstance(meld, list):
            raise ValueError(f"visible.melds[{index}] must be a JSON array")
    return VisibleTiles(
        discards=discards,
        melds=tuple(tuple(meld) for meld in melds),
        revealed=revealed,
    )


def _visible_region(value: object, section: str) -> VisibleRegionConfig:
    raw = _object(value, section)
    values = {
        key: _integer(raw, key, section)
        for key in ("x", "y", "slot_width", "slot_height", "stride", "count")
    }
    if values["x"] < 0 or values["y"] < 0:
        raise ValueError(f"{section}.x and {section}.y must be non-negative")
    if any(values[key] <= 0 for key in ("slot_width", "slot_height", "stride", "count")):
        raise ValueError(f"{section} geometry must be positive")
    return VisibleRegionConfig(**values)


def _visible_region_array(
    data: dict[str, object],
    key: str,
    section: str,
) -> tuple[VisibleRegionConfig, ...]:
    return tuple(
        _visible_region(region, f"{section}.{key}[{index}]")
        for index, region in enumerate(_optional_array(data, key, section))
    )


def _visible_regions(raw: dict[str, object]) -> VisibleRegionsConfig:
    regions_raw = raw.get("visible_regions", {})
    regions = _object(regions_raw, "visible_regions")
    return VisibleRegionsConfig(
        discards=_visible_region_array(regions, "discards", "visible_regions"),
        melds=_visible_region_array(regions, "melds", "visible_regions"),
        revealed=_visible_region_array(regions, "revealed", "visible_regions"),
    )


def load_config(path: str | Path) -> AppConfig:
    raw = _object(
        json.loads(Path(path).read_text(encoding="utf-8")),
        "configuration",
    )
    window_title = _required(raw, "window_title", "configuration")
    if not isinstance(window_title, str) or not window_title.strip():
        raise ValueError("configuration.window_title must be a nonempty string")

    hand_raw = _object(_required(raw, "hand", "configuration"), "hand")
    hand_values = {
        key: _integer(hand_raw, key, "hand")
        for key in ("x", "y", "slot_width", "slot_height", "stride", "count")
    }
    if hand_values["count"] != 14:
        raise ValueError("hand count must be exactly 14")
    if hand_values["x"] < 0 or hand_values["y"] < 0:
        raise ValueError("hand x and y must be non-negative")
    if any(
        hand_values[key] <= 0 for key in ("slot_width", "slot_height", "stride")
    ):
        raise ValueError("hand slot geometry must be positive")
    hand = HandConfig(**hand_values)

    matching_raw = _object(
        _required(raw, "matching", "configuration"), "matching"
    )
    threshold = _number(matching_raw, "threshold", "matching")
    min_margin = _number(matching_raw, "min_margin", "matching")
    if not 0 <= threshold <= 1 or not 0 <= min_margin <= 1:
        raise ValueError("matching threshold and min_margin must be between 0 and 1")
    matching = MatchingConfig(threshold=threshold, min_margin=min_margin)

    runtime_raw = _object(_required(raw, "runtime", "configuration"), "runtime")
    fps = _integer(runtime_raw, "fps", "runtime")
    stable_frames = _integer(runtime_raw, "stable_frames", "runtime")
    if fps <= 0 or stable_frames <= 0:
        raise ValueError("runtime fps and stable_frames must be positive")
    runtime = RuntimeConfig(fps=fps, stable_frames=stable_frames)

    advisor_raw = _object(_required(raw, "advisor", "configuration"), "advisor")
    advisor = AdvisorConfig(
        one_bamboo_weight=_number(
            advisor_raw, "one_bamboo_weight", "advisor"
        ),
        eight_dot_weight=_number(advisor_raw, "eight_dot_weight", "advisor"),
        pair_weight=_number(advisor_raw, "pair_weight", "advisor"),
    )

    return AppConfig(
        window_title=window_title,
        hand=hand,
        matching=matching,
        runtime=runtime,
        advisor=advisor,
        visible=_visible_tiles(raw),
        visible_regions=_visible_regions(raw),
    )
