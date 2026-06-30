from dataclasses import dataclass
import json
from pathlib import Path


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
    title: str
    hand: HandConfig
    matching: MatchingConfig
    runtime: RuntimeConfig
    advisor: AdvisorConfig


def load_config(path: str | Path) -> AppConfig:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    hand = HandConfig(**raw["hand"])
    matching = MatchingConfig(**raw["matching"])
    runtime = RuntimeConfig(**raw["runtime"])
    advisor = AdvisorConfig(**raw["advisor"])

    if hand.count != 14:
        raise ValueError("hand count must be exactly 14")
    if min(hand.x, hand.y, hand.slot_width, hand.slot_height, hand.stride) <= 0:
        raise ValueError("hand geometry must be positive")
    if not 0 <= matching.threshold <= 1:
        raise ValueError("matching threshold must be between 0 and 1")
    if runtime.fps <= 0 or runtime.stable_frames <= 0:
        raise ValueError("runtime fps and stable_frames must be positive")

    return AppConfig(
        title=raw["title"],
        hand=hand,
        matching=matching,
        runtime=runtime,
        advisor=advisor,
    )
