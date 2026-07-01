import json
from pathlib import Path
from time import perf_counter

import cv2
import pytest

from mahjong_vision.capture import crop_slots
from mahjong_vision.config import load_config
from mahjong_vision.templates import TemplateStore


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "samples" / "manifest.json"


@pytest.mark.skipif(not MANIFEST.exists(), reason="no labeled replay set")
def test_labeled_replay_accuracy_and_latency():
    config = load_config(ROOT / "config.json")
    store = TemplateStore(
        ROOT / "templates",
        (48, 72),
        config.matching.threshold,
        config.matching.min_margin,
    )
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
    correct = total = 0
    latencies = []
    for entry in entries:
        frame = cv2.imread(str(ROOT / "samples" / entry["image"]))
        assert frame is not None
        started = perf_counter()
        matches = [store.match(slot) for slot in crop_slots(frame, config.hand)]
        latencies.append((perf_counter() - started) * 1000)
        predicted = [match.label if match.accepted else None for match in matches]
        correct += sum(a == b for a, b in zip(predicted, entry["labels"]))
        total += 14
    accuracy = correct / total
    p95 = sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)]
    assert accuracy >= 0.99
    assert p95 < 100.0
