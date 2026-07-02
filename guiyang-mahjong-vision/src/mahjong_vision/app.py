from __future__ import annotations

from pathlib import Path
from queue import Queue
import sys
from threading import Event, Thread
from time import perf_counter, sleep

import numpy as np

from mahjong_vision.advisor import AdvisorWeights, advise
from mahjong_vision.capture import (
    WindowCapture,
    WindowUnavailable,
    detect_hand_slots,
    slot_has_tile,
)
from mahjong_vision.config import AppConfig, load_config
from mahjong_vision.domain import Tile
from mahjong_vision.overlay import Overlay, OverlayState
from mahjong_vision.recognizer import HandRecognizer, StableHand
from mahjong_vision.templates import TemplateStore
from mahjong_vision.visible_recognizer import VisibleTileRecognizer


def _plain_recommendation(reason: str, discard: str) -> str:
    discard_name = Tile.from_label(discard).display_name
    return f"优先打{discard_name}"


_BEFORE_DRAW_COUNTS = {1, 4, 7, 10, 13}
_AFTER_DRAW_COUNTS = {2, 5, 8, 11, 14}
_LEGAL_LIVE_COUNTS = _BEFORE_DRAW_COUNTS | _AFTER_DRAW_COUNTS


def _runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _display_hand(labels: tuple[str, ...]) -> str:
    return " ".join(Tile.from_label(label).display_name for label in labels)


def _append_visible_detail(detail: str, visible_counts: list[int]) -> str:
    visible_total = sum(visible_counts)
    if not visible_total:
        return detail
    return f"{detail}；已见 {visible_total} 张"


def _visible_counts_for_frame(
    frame: np.ndarray,
    config: AppConfig,
    recognizer: VisibleTileRecognizer,
) -> list[int]:
    configured_counts = config.visible.to_counts()
    if not config.visible_regions.has_regions():
        return configured_counts

    try:
        recognized = recognizer.recognize(frame, config.visible_regions)
    except ValueError:
        return configured_counts

    if not recognized.labels():
        return configured_counts
    return recognized.to_counts()


def _state_for_live_recognition(
    *,
    labels: tuple[str, ...],
    slot_count: int,
    unknown_count: int,
    elapsed_ms: float,
    weights: AdvisorWeights,
    visible_counts: list[int],
) -> OverlayState:
    display = _display_hand(labels)
    detail = _append_visible_detail(
        f"检测到 {slot_count} 张，未识别 {unknown_count} 张；识别 {elapsed_ms:.1f} ms",
        visible_counts,
    )

    if slot_count in _BEFORE_DRAW_COUNTS:
        return OverlayState(
            status=f"等待出牌：当前 {slot_count} 张",
            hand=display,
            recommendation="摸牌后再提示",
            detail=detail,
        )

    if slot_count in _AFTER_DRAW_COUNTS:
        if unknown_count:
            return OverlayState(
                status=f"该出牌：检测到 {slot_count} 张",
                hand=display,
                recommendation=f"该出牌，但有 {unknown_count} 张没识别",
                detail=detail,
            )
        if len(labels) != slot_count:
            return OverlayState(
                status=f"该出牌：检测到 {slot_count} 张",
                hand=display,
                recommendation="识别张数不完整，先别按建议打",
                detail=detail,
            )
        recommendation = advise(labels, weights, visible_counts)
        return OverlayState(
            status="该出牌",
            hand=display,
            recommendation=_plain_recommendation(
                recommendation.reason,
                recommendation.discard,
            ),
            detail=_append_visible_detail(
                f"检测到 {slot_count} 张；识别 {elapsed_ms:.1f} ms",
                visible_counts,
            ),
        )

    return OverlayState(
        status=f"实战识别中：当前 {slot_count} 张牌",
        hand=display,
        recommendation="当前张数不符合合法暗手形态，继续观察",
        detail=detail,
    )


def worker(
    config_path: Path,
    store: TemplateStore,
    updates: Queue[OverlayState],
    stop: Event,
) -> None:
    config = load_config(config_path)
    recognizer = HandRecognizer(store)
    visible_recognizer = VisibleTileRecognizer(store)
    stable = StableHand(config.runtime.stable_frames)
    weights = AdvisorWeights(
        config.advisor.one_bamboo_weight,
        config.advisor.eight_dot_weight,
        config.advisor.pair_weight,
    )
    interval = 1.0 / config.runtime.fps

    with WindowCapture(config.window_title) as capture:
        while not stop.is_set():
            started = perf_counter()
            try:
                frame = capture.capture()
                visible_counts = _visible_counts_for_frame(
                    frame,
                    config,
                    visible_recognizer,
                )
                slots = detect_hand_slots(frame)
                if not slots:
                    updates.put(OverlayState(status="等待摸牌：未检测到手牌"))
                    continue
                occupied = tuple(index for index, slot in enumerate(slots) if slot_has_tile(slot))
                occupied_slots = tuple(slots[index] for index in occupied)
                result = recognizer.recognize(occupied_slots)
                labels = tuple(label for label in result.labels if label)
                slot_count = len(slots)
                unknown_count = (len(slots) - len(occupied_slots)) + len(result.unknown_slots)

                if slot_count != 14 or unknown_count:
                    updates.put(
                        _state_for_live_recognition(
                            labels=labels,
                            slot_count=slot_count,
                            unknown_count=unknown_count,
                            elapsed_ms=result.elapsed_ms,
                            weights=weights,
                            visible_counts=visible_counts,
                        )
                    )
                    continue

                hand = stable.update(labels)
                if hand is None:
                    updates.put(OverlayState(status="等待画面稳定", hand=_display_hand(labels)))
                    continue

                updates.put(
                    _state_for_live_recognition(
                        labels=hand,
                        slot_count=slot_count,
                        unknown_count=unknown_count,
                        elapsed_ms=result.elapsed_ms,
                        weights=weights,
                        visible_counts=visible_counts,
                    )
                )
            except WindowUnavailable:
                updates.put(OverlayState(status="等待麻将窗口"))
            except (ValueError, OSError) as error:
                updates.put(OverlayState(status="当前画面不可用", detail=str(error)))

            elapsed = perf_counter() - started
            sleep(max(0.0, interval - elapsed))


def main() -> None:
    project_root = _runtime_root()
    config_path = project_root / "config.json"
    config = load_config(config_path)
    store = TemplateStore(
        project_root / "templates",
        size=(48, 72),
        threshold=config.matching.threshold,
        min_margin=config.matching.min_margin,
    )
    updates: Queue[OverlayState] = Queue()
    stop = Event()
    thread = Thread(
        target=worker,
        args=(config_path, store, updates, stop),
        daemon=True,
    )
    thread.start()
    overlay = Overlay(updates)
    try:
        overlay.run()
    finally:
        stop.set()
        thread.join(timeout=1.0)


if __name__ == "__main__":
    main()
