from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from uuid import uuid4

import cv2
import numpy as np

from mahjong_vision.domain import Tile
from mahjong_vision.image_ops import ProcessedImage, preprocess


@dataclass(frozen=True)
class MatchResult:
    label: str | None
    score: float
    runner_up_score: float
    accepted: bool


@dataclass(frozen=True)
class _TemplateSample:
    gray: np.ndarray
    edges: np.ndarray


def _unit_interval(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between 0 and 1")
    return float(value)


def _normalize_size(size: object) -> tuple[int, int]:
    if not isinstance(size, (list, tuple)) or len(size) != 2:
        raise ValueError("size must be a (width, height) pair")
    width, height = size
    if (
        type(width) is not int
        or type(height) is not int
        or width <= 0
        or height <= 0
    ):
        raise ValueError("size must contain positive integers")
    return (width, height)


def _validate_label(label: str) -> str:
    Tile.from_label(label)
    return label


def _sample_from_processed(processed: ProcessedImage) -> _TemplateSample:
    return _TemplateSample(gray=processed.gray, edges=processed.edges)


def _sample_from_file_image(image: np.ndarray, size: tuple[int, int]) -> _TemplateSample:
    if image.ndim == 2 and image.shape == (size[1], size[0]):
        gray = image.astype(np.uint8, copy=False)
        return _TemplateSample(gray=gray, edges=cv2.Canny(gray, 60, 140))
    return _sample_from_processed(preprocess(image, size))


def _correlation(first: np.ndarray, second: np.ndarray) -> float:
    first_values = first.astype(np.float32, copy=False).ravel()
    second_values = second.astype(np.float32, copy=False).ravel()
    first_centered = first_values - float(first_values.mean())
    second_centered = second_values - float(second_values.mean())
    denominator = float(
        np.linalg.norm(first_centered) * np.linalg.norm(second_centered)
    )
    if denominator == 0:
        return 0.0
    if np.array_equal(first, second):
        return 1.0
    score = float(np.dot(first_centered, second_centered) / denominator)
    return max(0.0, min(1.0, score))


class TemplateStore:
    def __init__(
        self,
        root: str | Path,
        size: object,
        threshold: float,
        min_margin: float,
    ) -> None:
        self.root = Path(root)
        self.size = _normalize_size(size)
        self.threshold = _unit_interval(threshold, "threshold")
        self.min_margin = _unit_interval(min_margin, "min_margin")
        self._lock = RLock()
        self._samples: dict[str, tuple[_TemplateSample, ...]] = {}
        self.reload()

    def reload(self) -> None:
        with self._lock:
            loaded: dict[str, tuple[_TemplateSample, ...]] = {}
            if self.root.exists():
                for label_dir in sorted(self.root.iterdir()):
                    if not label_dir.is_dir():
                        continue
                    try:
                        label = _validate_label(label_dir.name)
                    except ValueError:
                        continue

                    samples = []
                    for path in sorted(label_dir.glob("*.png")):
                        image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
                        if image is None:
                            continue
                        try:
                            samples.append(_sample_from_file_image(image, self.size))
                        except ValueError:
                            continue
                    if samples:
                        loaded[label] = tuple(samples)

            self._samples = loaded

    def add(self, label: str, image: np.ndarray) -> Path:
        label = _validate_label(label)
        sample = _sample_from_processed(preprocess(image, self.size))
        with self._lock:
            label_dir = self.root / label
            label_dir.mkdir(parents=True, exist_ok=True)

            path = label_dir / f"{uuid4().hex}.png"
            if not cv2.imwrite(str(path), sample.gray):
                raise OSError(f"failed to write template sample: {path}")

            existing = self._samples.get(label, ())
            self._samples[label] = (*existing, sample)
        return path

    def match(self, image: np.ndarray) -> MatchResult:
        query = _sample_from_processed(preprocess(image, self.size))
        with self._lock:
            samples = dict(self._samples)

        scores = [
            (
                label,
                max(
                    0.65 * _correlation(query.gray, sample.gray)
                    + 0.35 * _correlation(query.edges, sample.edges)
                    for sample in values
                ),
            )
            for label, values in samples.items()
            if values
        ]
        if not scores:
            return MatchResult(None, 0.0, 0.0, False)

        scores.sort(key=lambda item: item[1], reverse=True)
        label, score = scores[0]
        runner_up_score = scores[1][1] if len(scores) > 1 else 0.0
        accepted = (
            score >= self.threshold
            and score - runner_up_score >= self.min_margin
        )
        return MatchResult(label, score, runner_up_score, accepted)
