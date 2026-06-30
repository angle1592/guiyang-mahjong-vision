# Guiyang Mahjong Vision Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows-local OpenCV assistant that recognizes the 14 fixed hand slots in the current “多乐贵阳捉鸡麻将” window and displays a low-latency discard recommendation in an always-on-top overlay.

**Architecture:** A Win32/MSS capture adapter crops 14 configured slots. An OpenCV template store classifies each slot, a two-frame stabilizer rejects animation, and a pure-Python advisor ranks discards by shanten, effective draws, pairs, and configurable chicken weights. Tkinter owns the overlay and calibration dialog; a worker thread performs capture and analysis without blocking the UI.

**Tech Stack:** Python 3.11+, OpenCV, NumPy, MSS, pywin32, Tkinter, pytest

---

## File map

```text
guiyang-mahjong-vision/
  pyproject.toml                 Packaging, dependencies, pytest configuration
  config.json                   Fixed window and hand-slot geometry
  README.md                     Installation, calibration, and operation
  src/mahjong_vision/
    __init__.py
    domain.py                   Tile names, indices, and recognition value objects
    config.py                   Validated JSON configuration
    capture.py                  Win32 window lookup and MSS region capture
    image_ops.py                Deterministic OpenCV preprocessing
    templates.py                Template persistence and matching
    recognizer.py               Fourteen-slot recognition and frame stabilization
    advisor.py                  Shanten, effective draws, and discard ranking
    calibration.py              Low-confidence sample labeling dialog
    overlay.py                  Always-on-top status and recommendation window
    app.py                      Worker loop and UI orchestration
  tests/
    test_config.py
    test_image_ops.py
    test_templates.py
    test_recognizer.py
    test_advisor.py
    test_capture.py
  templates/.gitkeep
  samples/.gitkeep
```

### Task 1: Create the installable project and validated configuration

**Files:**
- Create: `guiyang-mahjong-vision/pyproject.toml`
- Create: `guiyang-mahjong-vision/config.json`
- Create: `guiyang-mahjong-vision/src/mahjong_vision/__init__.py`
- Create: `guiyang-mahjong-vision/src/mahjong_vision/config.py`
- Create: `guiyang-mahjong-vision/tests/test_config.py`
- Create: `guiyang-mahjong-vision/templates/.gitkeep`
- Create: `guiyang-mahjong-vision/samples/.gitkeep`

- [ ] **Step 1: Write the failing configuration tests**

```python
# guiyang-mahjong-vision/tests/test_config.py
import json

import pytest

from mahjong_vision.config import AppConfig, load_config


def test_load_config_builds_fourteen_slots(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "window_title": "多乐贵阳捉鸡麻将",
        "hand": {"x": 384, "y": 450, "slot_width": 62, "slot_height": 86,
                 "stride": 62, "count": 14},
        "matching": {"threshold": 0.82, "min_margin": 0.04},
        "runtime": {"fps": 20, "stable_frames": 2},
        "advisor": {"one_bamboo_weight": 2.0, "eight_dot_weight": 2.5,
                    "pair_weight": 0.4}
    }), encoding="utf-8")

    config = load_config(path)

    assert isinstance(config, AppConfig)
    assert len(config.hand.slot_rects()) == 14
    assert config.hand.slot_rects()[-1].x == 384 + 13 * 62


def test_invalid_slot_count_is_rejected(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "window_title": "x",
        "hand": {"x": 0, "y": 0, "slot_width": 1, "slot_height": 1,
                 "stride": 1, "count": 13},
        "matching": {"threshold": 0.8, "min_margin": 0.03},
        "runtime": {"fps": 20, "stable_frames": 2},
        "advisor": {"one_bamboo_weight": 1, "eight_dot_weight": 1,
                    "pair_weight": 0.1}
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="14"):
        load_config(path)
```

- [ ] **Step 2: Run the test and verify the expected import failure**

Run: `cd guiyang-mahjong-vision; python -m pytest tests/test_config.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'mahjong_vision'`.

- [ ] **Step 3: Add packaging, default configuration, and the minimal loader**

```toml
# guiyang-mahjong-vision/pyproject.toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "guiyang-mahjong-vision"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "mss>=10,<11",
  "numpy>=2,<3",
  "opencv-python>=4.10,<5",
  "pywin32>=308"
]

[project.optional-dependencies]
test = ["pytest>=8,<9"]

[project.scripts]
mahjong-vision = "mahjong_vision.app:main"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

```json
{
  "window_title": "多乐贵阳捉鸡麻将",
  "hand": {
    "x": 384,
    "y": 450,
    "slot_width": 62,
    "slot_height": 86,
    "stride": 62,
    "count": 14
  },
  "matching": {"threshold": 0.82, "min_margin": 0.04},
  "runtime": {"fps": 20, "stable_frames": 2},
  "advisor": {
    "one_bamboo_weight": 2.0,
    "eight_dot_weight": 2.5,
    "pair_weight": 0.4
  }
}
```

```python
# guiyang-mahjong-vision/src/mahjong_vision/config.py
from __future__ import annotations

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
            Rect(self.x + index * self.stride, self.y,
                 self.slot_width, self.slot_height)
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
    window_title: str
    hand: HandConfig
    matching: MatchingConfig
    runtime: RuntimeConfig
    advisor: AdvisorConfig


def load_config(path: str | Path) -> AppConfig:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    hand = HandConfig(**raw["hand"])
    if hand.count != 14:
        raise ValueError("hand slot count must be 14")
    if min(hand.slot_width, hand.slot_height, hand.stride) <= 0:
        raise ValueError("hand geometry must be positive")
    matching = MatchingConfig(**raw["matching"])
    if not 0.0 <= matching.threshold <= 1.0:
        raise ValueError("matching threshold must be between 0 and 1")
    runtime = RuntimeConfig(**raw["runtime"])
    if runtime.fps <= 0 or runtime.stable_frames <= 0:
        raise ValueError("runtime values must be positive")
    return AppConfig(
        window_title=raw["window_title"],
        hand=hand,
        matching=matching,
        runtime=runtime,
        advisor=AdvisorConfig(**raw["advisor"]),
    )
```

`__init__.py` is an empty UTF-8 file. Create empty `.gitkeep` files in `templates/` and `samples/`.

- [ ] **Step 4: Install and run the tests**

Run: `cd guiyang-mahjong-vision; python -m pip install -e ".[test]"; python -m pytest tests/test_config.py -v`

Expected: 2 passed.

- [ ] **Step 5: Commit**

Run:

```powershell
git add guiyang-mahjong-vision
git commit -m "build: scaffold mahjong vision assistant"
```

### Task 2: Define tile identities and deterministic image preprocessing

**Files:**
- Create: `guiyang-mahjong-vision/src/mahjong_vision/domain.py`
- Create: `guiyang-mahjong-vision/src/mahjong_vision/image_ops.py`
- Create: `guiyang-mahjong-vision/tests/test_image_ops.py`

- [ ] **Step 1: Write failing preprocessing and tile-code tests**

```python
# guiyang-mahjong-vision/tests/test_image_ops.py
import cv2
import numpy as np

from mahjong_vision.domain import Tile
from mahjong_vision.image_ops import preprocess


def test_tile_codes_cover_three_suits():
    assert Tile.from_label("1m").index == 0
    assert Tile.from_label("1p").index == 9
    assert Tile.from_label("1s").index == 18
    assert Tile.from_label("8p").display_name == "八筒"


def test_preprocess_normalizes_size_and_exposes_edges():
    image = np.zeros((60, 40, 3), dtype=np.uint8)
    cv2.rectangle(image, (10, 10), (30, 50), (255, 255, 255), 2)

    normalized = preprocess(image, size=(32, 48))

    assert normalized.gray.shape == (48, 32)
    assert normalized.edges.shape == (48, 32)
    assert int(normalized.edges.max()) == 255
```

- [ ] **Step 2: Run the tests and verify failure**

Run: `cd guiyang-mahjong-vision; python -m pytest tests/test_image_ops.py -v`

Expected: FAIL because `domain` and `image_ops` do not exist.

- [ ] **Step 3: Implement tile identities and preprocessing**

```python
# guiyang-mahjong-vision/src/mahjong_vision/domain.py
from __future__ import annotations

from dataclasses import dataclass

SUIT_NAMES = {"m": "万", "p": "筒", "s": "条"}
NUMERALS = "一二三四五六七八九"


@dataclass(frozen=True, order=True)
class Tile:
    index: int

    @classmethod
    def from_label(cls, label: str) -> "Tile":
        if len(label) != 2 or label[0] not in "123456789" or label[1] not in "mps":
            raise ValueError(f"invalid tile label: {label}")
        suit_offset = {"m": 0, "p": 9, "s": 18}[label[1]]
        return cls(suit_offset + int(label[0]) - 1)

    @property
    def label(self) -> str:
        suit = "mps"[self.index // 9]
        return f"{self.index % 9 + 1}{suit}"

    @property
    def display_name(self) -> str:
        return NUMERALS[self.index % 9] + SUIT_NAMES["mps"[self.index // 9]]


ALL_TILES = tuple(Tile(index) for index in range(27))
```

```python
# guiyang-mahjong-vision/src/mahjong_vision/image_ops.py
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class ProcessedImage:
    gray: np.ndarray
    edges: np.ndarray


def preprocess(image: np.ndarray, size: tuple[int, int]) -> ProcessedImage:
    if image.ndim == 3 and image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    elif image.ndim == 2:
        gray = image
    else:
        raise ValueError("image must be gray, BGR, or BGRA")
    gray = cv2.resize(gray, size, interpolation=cv2.INTER_AREA)
    gray = cv2.equalizeHist(gray)
    edges = cv2.Canny(gray, 60, 140)
    return ProcessedImage(gray=gray, edges=edges)
```

- [ ] **Step 4: Run tests**

Run: `cd guiyang-mahjong-vision; python -m pytest tests/test_image_ops.py -v`

Expected: 2 passed.

- [ ] **Step 5: Commit**

Run:

```powershell
git add guiyang-mahjong-vision/src/mahjong_vision/domain.py guiyang-mahjong-vision/src/mahjong_vision/image_ops.py guiyang-mahjong-vision/tests/test_image_ops.py
git commit -m "feat: add tile model and image preprocessing"
```

### Task 3: Persist and match exact game templates

**Files:**
- Create: `guiyang-mahjong-vision/src/mahjong_vision/templates.py`
- Create: `guiyang-mahjong-vision/tests/test_templates.py`

- [ ] **Step 1: Write failing template-store tests**

```python
# guiyang-mahjong-vision/tests/test_templates.py
import cv2
import numpy as np

from mahjong_vision.templates import TemplateStore


def tile_image(symbol: str) -> np.ndarray:
    image = np.full((86, 62, 3), 245, dtype=np.uint8)
    cv2.putText(image, symbol, (8, 58), cv2.FONT_HERSHEY_SIMPLEX,
                1.4, (0, 0, 0), 3, cv2.LINE_AA)
    return image


def test_saved_template_is_recognized(tmp_path):
    store = TemplateStore(tmp_path, size=(48, 72), threshold=0.75,
                          min_margin=0.02)
    store.add("1m", tile_image("1"))
    store.add("9m", tile_image("9"))

    result = store.match(tile_image("1"))

    assert result.label == "1m"
    assert result.accepted
    assert result.score > result.runner_up_score


def test_ambiguous_image_is_rejected(tmp_path):
    store = TemplateStore(tmp_path, size=(48, 72), threshold=0.99,
                          min_margin=0.20)
    store.add("1m", tile_image("1"))
    store.add("9m", tile_image("9"))

    result = store.match(np.full((86, 62, 3), 245, dtype=np.uint8))

    assert not result.accepted
```

- [ ] **Step 2: Verify failure**

Run: `cd guiyang-mahjong-vision; python -m pytest tests/test_templates.py -v`

Expected: FAIL because `TemplateStore` does not exist.

- [ ] **Step 3: Implement the template store**

```python
# guiyang-mahjong-vision/src/mahjong_vision/templates.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import RLock
import uuid

import cv2
import numpy as np

from .domain import Tile
from .image_ops import ProcessedImage, preprocess


@dataclass(frozen=True)
class MatchResult:
    label: str | None
    score: float
    runner_up_score: float
    accepted: bool


class TemplateStore:
    def __init__(self, root: str | Path, size: tuple[int, int],
                 threshold: float, min_margin: float) -> None:
        self.root = Path(root)
        self.size = size
        self.threshold = threshold
        self.min_margin = min_margin
        self._lock = RLock()
        self._templates: dict[str, list[ProcessedImage]] = {}
        self.reload()

    def reload(self) -> None:
        with self._lock:
            self._templates.clear()
            if not self.root.exists():
                return
            for path in self.root.glob("*/*.png"):
                image = cv2.imread(str(path), cv2.IMREAD_COLOR)
                if image is not None:
                    self._templates.setdefault(path.parent.name, []).append(
                        preprocess(image, self.size)
                    )

    def add(self, label: str, image: np.ndarray) -> Path:
        Tile.from_label(label)
        folder = self.root / label
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{uuid.uuid4().hex}.png"
        if not cv2.imwrite(str(path), image):
            raise OSError(f"failed to write template {path}")
        with self._lock:
            self._templates.setdefault(label, []).append(
                preprocess(image, self.size)
            )
        return path

    @staticmethod
    def _score(left: ProcessedImage, right: ProcessedImage) -> float:
        gray = float(cv2.matchTemplate(
            left.gray, right.gray, cv2.TM_CCOEFF_NORMED
        )[0, 0])
        edge = float(cv2.matchTemplate(
            left.edges, right.edges, cv2.TM_CCOEFF_NORMED
        )[0, 0])
        if not np.isfinite(gray):
            gray = 0.0
        if not np.isfinite(edge):
            edge = 0.0
        return 0.65 * gray + 0.35 * edge

    def match(self, image: np.ndarray) -> MatchResult:
        candidate = preprocess(image, self.size)
        with self._lock:
            label_scores = {
                label: max(
                    self._score(candidate, template) for template in samples
                )
                for label, samples in self._templates.items()
            }
        if not label_scores:
            return MatchResult(None, 0.0, 0.0, False)
        ordered = sorted(label_scores.items(), key=lambda item: item[1],
                         reverse=True)
        best_label, best_score = ordered[0]
        runner_up = ordered[1][1] if len(ordered) > 1 else 0.0
        accepted = (
            best_score >= self.threshold
            and best_score - runner_up >= self.min_margin
        )
        return MatchResult(best_label, best_score, runner_up, accepted)
```

- [ ] **Step 4: Run tests**

Run: `cd guiyang-mahjong-vision; python -m pytest tests/test_templates.py -v`

Expected: 2 passed.

- [ ] **Step 5: Commit**

Run:

```powershell
git add guiyang-mahjong-vision/src/mahjong_vision/templates.py guiyang-mahjong-vision/tests/test_templates.py
git commit -m "feat: add OpenCV template matching"
```

### Task 4: Capture the fixed WeChat window slots

**Files:**
- Create: `guiyang-mahjong-vision/src/mahjong_vision/capture.py`
- Create: `guiyang-mahjong-vision/tests/test_capture.py`

- [ ] **Step 1: Write failing geometry tests using an injected frame source**

```python
# guiyang-mahjong-vision/tests/test_capture.py
import numpy as np

from mahjong_vision.capture import crop_slots
from mahjong_vision.config import HandConfig


def test_crop_slots_uses_configured_stride():
    frame = np.zeros((100, 220, 3), dtype=np.uint8)
    frame[:, 10:30] = 10
    frame[:, 40:60] = 40
    hand = HandConfig(x=10, y=20, slot_width=20, slot_height=30,
                      stride=30, count=14)

    slots = crop_slots(frame, hand)

    assert len(slots) == 14
    assert slots[0].shape == (30, 20, 3)
    assert int(slots[0].mean()) == 10
    assert int(slots[1].mean()) == 40


def test_out_of_bounds_slot_is_rejected():
    frame = np.zeros((20, 20, 3), dtype=np.uint8)
    hand = HandConfig(x=0, y=0, slot_width=10, slot_height=10,
                      stride=10, count=14)

    try:
        crop_slots(frame, hand)
    except ValueError as error:
        assert "outside" in str(error)
    else:
        raise AssertionError("expected out-of-bounds failure")
```

- [ ] **Step 2: Verify failure**

Run: `cd guiyang-mahjong-vision; python -m pytest tests/test_capture.py -v`

Expected: FAIL because `capture` does not exist.

- [ ] **Step 3: Implement Win32/MSS capture and pure slot cropping**

```python
# guiyang-mahjong-vision/src/mahjong_vision/capture.py
from __future__ import annotations

from dataclasses import dataclass

import mss
import numpy as np
import win32gui

from .config import HandConfig


class WindowUnavailable(RuntimeError):
    pass


def crop_slots(frame: np.ndarray, hand: HandConfig) -> tuple[np.ndarray, ...]:
    slots: list[np.ndarray] = []
    height, width = frame.shape[:2]
    for rect in hand.slot_rects():
        if rect.x < 0 or rect.y < 0 or rect.x + rect.width > width or \
                rect.y + rect.height > height:
            raise ValueError("configured hand slot is outside captured frame")
        slots.append(frame[
            rect.y:rect.y + rect.height,
            rect.x:rect.x + rect.width
        ].copy())
    return tuple(slots)


@dataclass
class WindowCapture:
    title: str

    def __post_init__(self) -> None:
        self._mss = mss.mss()

    def capture(self) -> np.ndarray:
        hwnd = win32gui.FindWindow(None, self.title)
        if not hwnd or win32gui.IsIconic(hwnd):
            raise WindowUnavailable(f"window unavailable: {self.title}")
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        if right <= left or bottom <= top:
            raise WindowUnavailable("window has invalid bounds")
        shot = self._mss.grab({
            "left": left, "top": top,
            "width": right - left, "height": bottom - top
        })
        return np.asarray(shot)
```

- [ ] **Step 4: Run tests**

Run: `cd guiyang-mahjong-vision; python -m pytest tests/test_capture.py -v`

Expected: 2 passed.

- [ ] **Step 5: Commit**

Run:

```powershell
git add guiyang-mahjong-vision/src/mahjong_vision/capture.py guiyang-mahjong-vision/tests/test_capture.py
git commit -m "feat: capture fixed mahjong hand slots"
```

### Task 5: Recognize and stabilize complete hands

**Files:**
- Create: `guiyang-mahjong-vision/src/mahjong_vision/recognizer.py`
- Create: `guiyang-mahjong-vision/tests/test_recognizer.py`

- [ ] **Step 1: Write failing recognition and stabilization tests**

```python
# guiyang-mahjong-vision/tests/test_recognizer.py
from dataclasses import dataclass

import numpy as np

from mahjong_vision.recognizer import HandRecognizer, StableHand
from mahjong_vision.templates import MatchResult


@dataclass
class FakeStore:
    results: list[MatchResult]

    def match(self, image):
        return self.results.pop(0)


def test_unknown_slot_blocks_complete_hand():
    accepted = MatchResult("1m", 0.95, 0.2, True)
    unknown = MatchResult("9m", 0.60, 0.59, False)
    store = FakeStore([accepted] * 13 + [unknown])

    result = HandRecognizer(store).recognize(
        tuple(np.zeros((2, 2, 3), dtype=np.uint8) for _ in range(14))
    )

    assert not result.complete
    assert result.unknown_slots == (13,)


def test_two_matching_frames_become_stable():
    stable = StableHand(required_frames=2)
    hand = tuple(["1m"] * 14)

    assert stable.update(hand) is None
    assert stable.update(hand) == hand
```

- [ ] **Step 2: Verify failure**

Run: `cd guiyang-mahjong-vision; python -m pytest tests/test_recognizer.py -v`

Expected: FAIL because `recognizer` does not exist.

- [ ] **Step 3: Implement recognition values and frame stabilization**

```python
# guiyang-mahjong-vision/src/mahjong_vision/recognizer.py
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Protocol

import numpy as np

from .templates import MatchResult


class Matcher(Protocol):
    def match(self, image: np.ndarray) -> MatchResult: ...


@dataclass(frozen=True)
class Recognition:
    labels: tuple[str | None, ...]
    scores: tuple[float, ...]
    unknown_slots: tuple[int, ...]
    elapsed_ms: float

    @property
    def complete(self) -> bool:
        return len(self.labels) == 14 and not self.unknown_slots


class HandRecognizer:
    def __init__(self, store: Matcher) -> None:
        self.store = store

    def recognize(self, slots: tuple[np.ndarray, ...]) -> Recognition:
        started = perf_counter()
        matches = tuple(self.store.match(slot) for slot in slots)
        unknown = tuple(
            index for index, match in enumerate(matches) if not match.accepted
        )
        labels = tuple(
            match.label if match.accepted else None for match in matches
        )
        return Recognition(
            labels=labels,
            scores=tuple(match.score for match in matches),
            unknown_slots=unknown,
            elapsed_ms=(perf_counter() - started) * 1000,
        )


class StableHand:
    def __init__(self, required_frames: int) -> None:
        self.required_frames = required_frames
        self._last: tuple[str, ...] | None = None
        self._count = 0

    def update(self, hand: tuple[str, ...]) -> tuple[str, ...] | None:
        if hand == self._last:
            self._count += 1
        else:
            self._last = hand
            self._count = 1
        return hand if self._count >= self.required_frames else None
```

- [ ] **Step 4: Run tests**

Run: `cd guiyang-mahjong-vision; python -m pytest tests/test_recognizer.py -v`

Expected: 2 passed.

- [ ] **Step 5: Commit**

Run:

```powershell
git add guiyang-mahjong-vision/src/mahjong_vision/recognizer.py guiyang-mahjong-vision/tests/test_recognizer.py
git commit -m "feat: recognize and stabilize hands"
```

### Task 6: Rank discards with tile efficiency and Guizhou weights

**Files:**
- Create: `guiyang-mahjong-vision/src/mahjong_vision/advisor.py`
- Create: `guiyang-mahjong-vision/tests/test_advisor.py`

- [ ] **Step 1: Write failing advisor tests**

```python
# guiyang-mahjong-vision/tests/test_advisor.py
from mahjong_vision.advisor import AdvisorWeights, advise


def test_isolated_nine_is_discarded_from_pair_rich_hand():
    hand = ("5m", "6m", "6m", "9m", "2s", "2s", "3s",
            "8s", "1p", "1p", "1p", "6p", "6p", "8s")

    result = advise(hand, AdvisorWeights(2.0, 2.5, 0.4))

    assert result.discard == "9m"
    assert result.shanten_after <= result.alternatives[-1].shanten_after


def test_chicken_weight_does_not_preserve_tile_at_cost_of_shanten():
    hand = ("1s", "1m", "2m", "3m", "4m", "5m", "6m",
            "2p", "3p", "4p", "6p", "7p", "8p", "9p")

    result = advise(hand, AdvisorWeights(2.0, 2.5, 0.4))

    assert result.discard == "1s"


def test_fourteen_tiles_are_required():
    try:
        advise(("1m",), AdvisorWeights(2.0, 2.5, 0.4))
    except ValueError as error:
        assert "14" in str(error)
    else:
        raise AssertionError("expected invalid-hand failure")
```

- [ ] **Step 2: Verify failure**

Run: `cd guiyang-mahjong-vision; python -m pytest tests/test_advisor.py -v`

Expected: FAIL because `advisor` does not exist.

- [ ] **Step 3: Implement shanten, effective draws, and deterministic ranking**

```python
# guiyang-mahjong-vision/src/mahjong_vision/advisor.py
from __future__ import annotations

from dataclasses import dataclass

from .domain import Tile


@dataclass(frozen=True)
class AdvisorWeights:
    one_bamboo: float
    eight_dot: float
    pair: float


@dataclass(frozen=True)
class Alternative:
    discard: str
    shanten_after: int
    effective_tiles: int
    keep_value: float


@dataclass(frozen=True)
class Advice:
    discard: str
    reason: str
    shanten_after: int
    alternatives: tuple[Alternative, ...]


def _standard_shanten(counts: list[int]) -> int:
    best = 8

    def walk(index: int, melds: int, pairs: int, taatsu: int) -> None:
        nonlocal best
        while index < 27 and counts[index] == 0:
            index += 1
        if index == 27:
            usable_taatsu = min(taatsu, 4 - melds)
            best = min(best, 8 - 2 * melds - usable_taatsu - min(pairs, 1))
            return

        walk(index + 1, melds, pairs, taatsu)

        if counts[index] >= 3:
            counts[index] -= 3
            walk(index, melds + 1, pairs, taatsu)
            counts[index] += 3

        suit_position = index % 9
        if suit_position <= 6 and counts[index + 1] and counts[index + 2]:
            counts[index] -= 1
            counts[index + 1] -= 1
            counts[index + 2] -= 1
            walk(index, melds + 1, pairs, taatsu)
            counts[index] += 1
            counts[index + 1] += 1
            counts[index + 2] += 1

        if counts[index] >= 2:
            counts[index] -= 2
            walk(index, melds, pairs + 1, taatsu)
            walk(index, melds, pairs, taatsu + 1)
            counts[index] += 2

        if suit_position <= 7 and counts[index + 1]:
            counts[index] -= 1
            counts[index + 1] -= 1
            walk(index, melds, pairs, taatsu + 1)
            counts[index] += 1
            counts[index + 1] += 1

        if suit_position <= 6 and counts[index + 2]:
            counts[index] -= 1
            counts[index + 2] -= 1
            walk(index, melds, pairs, taatsu + 1)
            counts[index] += 1
            counts[index + 2] += 1

    walk(0, 0, 0, 0)
    return best


def _seven_pairs_shanten(counts: list[int]) -> int:
    pair_types = sum(count >= 2 for count in counts)
    distinct = sum(count > 0 for count in counts)
    return 6 - pair_types + max(0, 7 - distinct)


def _shanten(counts: list[int]) -> int:
    return min(_standard_shanten(counts.copy()), _seven_pairs_shanten(counts))


def _best_after_draw(counts: list[int]) -> int:
    best = 8
    for discard_index, count in enumerate(counts):
        if count:
            counts[discard_index] -= 1
            best = min(best, _shanten(counts))
            counts[discard_index] += 1
    return best


def _effective_draws(counts: list[int], base_shanten: int) -> int:
    total = 0
    for draw_index, count in enumerate(counts):
        if count >= 4:
            continue
        counts[draw_index] += 1
        if _best_after_draw(counts) < base_shanten:
            total += 4 - count
        counts[draw_index] -= 1
    return total


def _keep_value(tile: Tile, original_count: int,
                weights: AdvisorWeights) -> float:
    value = weights.pair if original_count >= 2 else 0.0
    if tile.label == "1s":
        value += weights.one_bamboo
    if tile.label == "8p":
        value += weights.eight_dot
    return value


def advise(labels: tuple[str, ...], weights: AdvisorWeights) -> Advice:
    if len(labels) != 14:
        raise ValueError("advisor requires exactly 14 tiles")
    counts = [0] * 27
    for label in labels:
        tile = Tile.from_label(label)
        counts[tile.index] += 1
        if counts[tile.index] > 4:
            raise ValueError(f"too many copies of {label}")

    alternatives: list[Alternative] = []
    for tile_index, original_count in enumerate(counts):
        if not original_count:
            continue
        tile = Tile(tile_index)
        counts[tile_index] -= 1
        shanten = _shanten(counts)
        effective = _effective_draws(counts, shanten)
        counts[tile_index] += 1
        alternatives.append(Alternative(
            discard=tile.label,
            shanten_after=shanten,
            effective_tiles=effective,
            keep_value=_keep_value(tile, original_count, weights),
        ))

    alternatives.sort(key=lambda item: (
        item.shanten_after,
        -item.effective_tiles,
        item.keep_value,
        Tile.from_label(item.discard).index,
    ))
    best = alternatives[0]
    reason = (
        f"打{Tile.from_label(best.discard).display_name}："
        f"向听数{best.shanten_after}，有效进张{best.effective_tiles}张"
    )
    return Advice(best.discard, reason, best.shanten_after,
                  tuple(alternatives))
```

- [ ] **Step 4: Run advisor tests and adjust only if a test exposes an algorithm defect**

Run: `cd guiyang-mahjong-vision; python -m pytest tests/test_advisor.py -v`

Expected: 3 passed.

- [ ] **Step 5: Run the complete suite**

Run: `cd guiyang-mahjong-vision; python -m pytest -q`

Expected: all tests pass.

- [ ] **Step 6: Commit**

Run:

```powershell
git add guiyang-mahjong-vision/src/mahjong_vision/advisor.py guiyang-mahjong-vision/tests/test_advisor.py
git commit -m "feat: recommend efficient Guizhou discards"
```

### Task 7: Add the calibration dialog and always-on-top overlay

**Files:**
- Create: `guiyang-mahjong-vision/src/mahjong_vision/calibration.py`
- Create: `guiyang-mahjong-vision/src/mahjong_vision/overlay.py`

- [ ] **Step 1: Implement a calibration dialog that saves exactly one selected sample**

```python
# guiyang-mahjong-vision/src/mahjong_vision/calibration.py
from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk

import numpy as np

from .domain import ALL_TILES
from .templates import TemplateStore


@dataclass(frozen=True)
class CalibrationRequest:
    slot_image: np.ndarray
    slot_index: int


class CalibrationDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, store: TemplateStore,
                 slot_image: np.ndarray, slot_index: int) -> None:
        super().__init__(parent)
        self.title(f"标注第 {slot_index + 1} 张牌")
        self.attributes("-topmost", True)
        self.resizable(False, False)
        self.store = store
        self.slot_image = slot_image.copy()
        self.label_by_name = {
            tile.display_name: tile.label for tile in ALL_TILES
        }
        self.choice = tk.StringVar(value=ALL_TILES[0].display_name)
        ttk.Label(self, text=f"低置信度牌槽：{slot_index + 1}").pack(
            padx=12, pady=(12, 4)
        )
        ttk.Combobox(
            self, textvariable=self.choice,
            values=list(self.label_by_name), state="readonly", width=12
        ).pack(padx=12, pady=4)
        ttk.Button(self, text="保存模板", command=self._save).pack(
            padx=12, pady=(4, 12)
        )

    def _save(self) -> None:
        self.store.add(self.label_by_name[self.choice.get()], self.slot_image)
        self.destroy()
```

- [ ] **Step 2: Implement the overlay with a thread-safe queue boundary**

```python
# guiyang-mahjong-vision/src/mahjong_vision/overlay.py
from __future__ import annotations

from dataclasses import dataclass
from queue import Empty, Queue
import tkinter as tk
from tkinter import ttk

from .calibration import CalibrationDialog, CalibrationRequest
from .templates import TemplateStore


@dataclass(frozen=True)
class OverlayState:
    status: str
    hand: str = ""
    recommendation: str = ""
    detail: str = ""


class Overlay:
    def __init__(self, updates: Queue[OverlayState],
                 calibration_requests: Queue[CalibrationRequest],
                 store: TemplateStore) -> None:
        self.updates = updates
        self.calibration_requests = calibration_requests
        self.store = store
        self.calibration_dialog: CalibrationDialog | None = None
        self.root = tk.Tk()
        self.root.title("贵阳捉鸡识牌助手")
        self.root.attributes("-topmost", True)
        self.root.geometry("520x128+720+20")
        self.status = tk.StringVar(value="正在启动")
        self.hand = tk.StringVar(value="")
        self.recommendation = tk.StringVar(value="")
        self.detail = tk.StringVar(value="")
        for variable, font in (
            (self.status, ("Microsoft YaHei UI", 10)),
            (self.hand, ("Microsoft YaHei UI", 10)),
            (self.recommendation, ("Microsoft YaHei UI", 15, "bold")),
            (self.detail, ("Microsoft YaHei UI", 9)),
        ):
            ttk.Label(self.root, textvariable=variable, font=font).pack(
                anchor="w", padx=10, pady=2
            )
        self.root.after(20, self._drain)
        self.root.after(50, self._drain_calibration)

    def _drain(self) -> None:
        latest = None
        try:
            while True:
                latest = self.updates.get_nowait()
        except Empty:
            pass
        if latest is not None:
            self.status.set(latest.status)
            self.hand.set(latest.hand)
            self.recommendation.set(latest.recommendation)
            self.detail.set(latest.detail)
        self.root.after(20, self._drain)

    def _drain_calibration(self) -> None:
        if self.calibration_dialog is not None and \
                self.calibration_dialog.winfo_exists():
            self.root.after(50, self._drain_calibration)
            return
        self.calibration_dialog = None
        try:
            request = self.calibration_requests.get_nowait()
        except Empty:
            self.root.after(50, self._drain_calibration)
            return
        self.calibration_dialog = CalibrationDialog(
            self.root, self.store, request.slot_image, request.slot_index
        )
        self.root.after(50, self._drain_calibration)

    def run(self) -> None:
        self.root.mainloop()
```

- [ ] **Step 3: Verify imports without opening UI**

Run:

```powershell
cd guiyang-mahjong-vision
python -c "from mahjong_vision.calibration import CalibrationDialog; from mahjong_vision.overlay import Overlay, OverlayState; print('ok')"
```

Expected: `ok`.

- [ ] **Step 4: Commit**

Run:

```powershell
git add guiyang-mahjong-vision/src/mahjong_vision/calibration.py guiyang-mahjong-vision/src/mahjong_vision/overlay.py
git commit -m "feat: add calibration and overlay UI"
```

### Task 8: Wire the real-time application and document calibration

**Files:**
- Create: `guiyang-mahjong-vision/src/mahjong_vision/app.py`
- Create: `guiyang-mahjong-vision/README.md`

- [ ] **Step 1: Implement the worker loop without any input automation**

```python
# guiyang-mahjong-vision/src/mahjong_vision/app.py
from __future__ import annotations

from pathlib import Path
from queue import Queue
from threading import Event, Thread
from time import perf_counter, sleep

from .advisor import AdvisorWeights, advise
from .calibration import CalibrationRequest
from .capture import WindowCapture, WindowUnavailable, crop_slots
from .config import load_config
from .domain import Tile
from .overlay import Overlay, OverlayState
from .recognizer import HandRecognizer, StableHand
from .templates import TemplateStore


def worker(config_path: Path, store: TemplateStore,
           updates: Queue[OverlayState],
           calibration_requests: Queue[CalibrationRequest],
           stop: Event) -> None:
    config = load_config(config_path)
    capture = WindowCapture(config.window_title)
    recognizer = HandRecognizer(store)
    stable = StableHand(config.runtime.stable_frames)
    weights = AdvisorWeights(
        config.advisor.one_bamboo_weight,
        config.advisor.eight_dot_weight,
        config.advisor.pair_weight,
    )
    interval = 1.0 / config.runtime.fps

    while not stop.is_set():
        started = perf_counter()
        try:
            frame = capture.capture()
            slots = crop_slots(frame, config.hand)
            result = recognizer.recognize(slots)
            if not result.complete:
                if calibration_requests.empty():
                    first_unknown = result.unknown_slots[0]
                    calibration_requests.put(CalibrationRequest(
                        slot_image=slots[first_unknown].copy(),
                        slot_index=first_unknown,
                    ))
                updates.put(OverlayState(
                    status=f"需要标注：牌槽 {', '.join(str(i + 1) for i in result.unknown_slots)}",
                    detail=f"识别耗时 {result.elapsed_ms:.1f} ms",
                ))
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
                    updates.put(OverlayState(
                        status="识别完成",
                        hand=display,
                        recommendation=(
                            "推荐打出：" +
                            Tile.from_label(recommendation.discard).display_name
                        ),
                        detail=(
                            f"{recommendation.reason}；"
                            f"最低置信度 {min(result.scores):.3f}；"
                            f"识别 {result.elapsed_ms:.1f} ms"
                        ),
                    ))
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
```

- [ ] **Step 2: Write operational documentation**

```markdown
# 贵阳捉鸡麻将识牌助手

本程序只识别当前电脑上的“多乐贵阳捉鸡麻将”固定窗口，并在置顶小窗
显示弃牌建议；它不会自动点击或代打。

## 安装

```powershell
python -m pip install -e ".[test]"
```

## 启动

1. 打开微信小程序并保持窗口可见。
2. 保持 Windows 显示缩放和小程序窗口尺寸不变。
3. 运行：

```powershell
mahjong-vision
```

## 配置坐标

`config.json` 中的 `hand.x` 和 `hand.y` 是第一张手牌左上角相对小程序
窗口的位置；`slot_width`、`slot_height` 和 `stride` 定义固定牌槽。

## 模板

模板按 `templates/1m/`、`templates/2m/`、`templates/1p/`、
`templates/1s/` 等目录保存。万、筒、条分别使用 `m`、`p`、`s`。
每种牌可以保存多个普通、选中和高亮状态样本。

低置信度时助手不会给出建议。使用标注窗口保存正确标签后，下一帧即可
使用新模板。

## 验证

```powershell
python -m pytest -q
```
```

- [ ] **Step 3: Run all tests and import the entry point**

Run:

```powershell
cd guiyang-mahjong-vision
python -m pytest -q
python -c "from mahjong_vision.app import main; print('entry point ok')"
```

Expected: all tests pass, followed by `entry point ok`.

- [ ] **Step 4: Launch for the first manual geometry check**

Run: `cd guiyang-mahjong-vision; mahjong-vision`

Expected: the overlay opens, remains above ordinary windows, and shows either `等待麻将窗口` or a low-confidence/template status. It must not send mouse or keyboard input.

- [ ] **Step 5: Commit**

Run:

```powershell
git add guiyang-mahjong-vision/src/mahjong_vision/app.py guiyang-mahjong-vision/README.md
git commit -m "feat: run real-time mahjong vision overlay"
```

### Task 9: Add replay accuracy and latency verification

**Files:**
- Create: `guiyang-mahjong-vision/tests/test_replay.py`
- Modify: `guiyang-mahjong-vision/README.md`

- [ ] **Step 1: Add a replay test that skips cleanly until labeled samples exist**

```python
# guiyang-mahjong-vision/tests/test_replay.py
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
        ROOT / "templates", (48, 72),
        config.matching.threshold, config.matching.min_margin
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
```

- [ ] **Step 2: Document the replay manifest format**

Append to `README.md`:

```markdown
## 回放数据格式

`samples/manifest.json`：

```json
[
  {
    "image": "hand-001.png",
    "labels": [
      "5m", "6m", "6m", "9m", "2s", "2s", "3s",
      "8s", "1p", "1p", "1p", "6p", "6p", "8s"
    ]
  }
]
```

加入标注截图后运行 `python -m pytest tests/test_replay.py -v`，测试会检查
单牌准确率与第 95 百分位延迟。
```

- [ ] **Step 3: Run the full suite**

Run: `cd guiyang-mahjong-vision; python -m pytest -q`

Expected: all unit tests pass and replay test reports SKIPPED until a manifest is added.

- [ ] **Step 4: Commit**

Run:

```powershell
git add guiyang-mahjong-vision/tests/test_replay.py guiyang-mahjong-vision/README.md
git commit -m "test: verify replay accuracy and latency"
```

## Final verification

- [ ] Run: `cd guiyang-mahjong-vision; python -m pytest -q`

Expected: all deterministic tests pass; replay test is either passing or skipped only because no labeled replay set exists.

- [ ] Run: `cd guiyang-mahjong-vision; python -m pip check`

Expected: `No broken requirements found.`

- [ ] Start the app beside the open WeChat mini-program and verify:

  - the overlay remains outside the configured hand region;
  - unknown slots never produce a discard recommendation;
  - two identical frames are required before a recommendation;
  - no mouse or keyboard input is generated;
  - observed processing latency is below 100 ms at the 95th percentile after templates are populated.
