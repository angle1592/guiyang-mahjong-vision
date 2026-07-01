from __future__ import annotations

from pathlib import Path
from queue import Queue
from threading import Event, Thread
from time import perf_counter, sleep

from mahjong_vision.advisor import AdvisorWeights, advise
from mahjong_vision.calibration import CalibrationRequest
from mahjong_vision.capture import WindowCapture, WindowUnavailable, crop_slots
from mahjong_vision.config import load_config
from mahjong_vision.domain import Tile
from mahjong_vision.overlay import Overlay, OverlayState
from mahjong_vision.recognizer import HandRecognizer, StableHand
from mahjong_vision.templates import TemplateStore


def worker(
    config_path: Path,
    store: TemplateStore,
    updates: Queue[OverlayState],
    calibration_requests: Queue[CalibrationRequest],
    stop: Event,
) -> None:
    config = load_config(config_path)
    recognizer = HandRecognizer(store)
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
                slots = crop_slots(frame, config.hand)
                result = recognizer.recognize(slots)
                if not result.complete:
                    if result.unknown_slots and calibration_requests.empty():
                        first_unknown = result.unknown_slots[0]
                        calibration_requests.put(
                            CalibrationRequest(
                                slot_image=slots[first_unknown].copy(),
                                slot_index=first_unknown,
                            )
                        )
                    updates.put(
                        OverlayState(
                            status=(
                                "需要标注：牌槽 "
                                + ", ".join(
                                    str(index + 1) for index in result.unknown_slots
                                )
                            ),
                            detail=f"识别耗时 {result.elapsed_ms:.1f} ms",
                        )
                    )
                else:
                    labels = tuple(label for label in result.labels if label)
                    hand = stable.update(labels)
                    if hand is None:
                        updates.put(OverlayState(status="等待画面稳定"))
                    else:
                        recommendation = advise(hand, weights)
                        display = " ".join(
                            Tile.from_label(label).display_name for label in hand
                        )
                        updates.put(
                            OverlayState(
                                status="识别完成",
                                hand=display,
                                recommendation=(
                                    "推荐打出："
                                    + Tile.from_label(
                                        recommendation.discard
                                    ).display_name
                                ),
                                detail=(
                                    f"{recommendation.reason}；"
                                    f"最低置信度 {min(result.scores):.3f}；"
                                    f"识别 {result.elapsed_ms:.1f} ms"
                                ),
                            )
                        )
            except WindowUnavailable:
                updates.put(OverlayState(status="等待麻将窗口"))
            except (ValueError, OSError) as error:
                updates.put(OverlayState(status="当前画面不可用", detail=str(error)))

            elapsed = perf_counter() - started
            sleep(max(0.0, interval - elapsed))


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    config_path = project_root / "config.json"
    config = load_config(config_path)
    store = TemplateStore(
        project_root / "templates",
        size=(48, 72),
        threshold=config.matching.threshold,
        min_margin=config.matching.min_margin,
    )
    updates: Queue[OverlayState] = Queue()
    calibration_requests: Queue[CalibrationRequest] = Queue(maxsize=1)
    stop = Event()
    thread = Thread(
        target=worker,
        args=(config_path, store, updates, calibration_requests, stop),
        daemon=True,
    )
    thread.start()
    overlay = Overlay(updates, calibration_requests, store)
    try:
        overlay.run()
    finally:
        stop.set()
        thread.join(timeout=1.0)


if __name__ == "__main__":
    main()
