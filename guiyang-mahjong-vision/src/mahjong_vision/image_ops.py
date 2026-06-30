from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True, eq=False)
class ProcessedImage:
    gray: np.ndarray
    edges: np.ndarray


def _normalize_uint8(image: np.ndarray) -> np.ndarray:
    if image.dtype.kind == "f":
        if not np.isfinite(image).all():
            raise ValueError("floating-point image values must be finite")
        image = np.clip(image, 0, 1) * 255
    elif image.dtype.kind not in "iu":
        raise ValueError("image dtype must be an integer or floating-point type")
    return np.clip(image, 0, 255).astype(np.uint8)


def preprocess(image: np.ndarray, size: tuple[int, int]) -> ProcessedImage:
    """Preprocess a gray, BGR, or BGRA image to ``size=(width, height)``.

    Color arrays use BGR/BGRA ordering. Finite floats are normalized-domain
    values clipped to [0, 1] and scaled to uint8; integers clip to [0, 255].
    """
    if (
        not isinstance(size, tuple)
        or len(size) != 2
        or any(type(dimension) is not int or dimension <= 0 for dimension in size)
    ):
        raise ValueError("size must be a (width, height) tuple of positive integers")
    if not isinstance(image, np.ndarray) or image.size == 0:
        raise ValueError("image must be a non-empty numpy array")

    normalized = _normalize_uint8(image)
    if normalized.ndim == 2:
        gray = normalized
    elif normalized.ndim == 3 and normalized.shape[2] == 3:
        gray = cv2.cvtColor(normalized, cv2.COLOR_BGR2GRAY)
    elif normalized.ndim == 3 and normalized.shape[2] == 4:
        gray = cv2.cvtColor(normalized, cv2.COLOR_BGRA2GRAY)
    else:
        raise ValueError("image must be grayscale, BGR, or BGRA")

    resized = cv2.resize(gray, size, interpolation=cv2.INTER_AREA)
    equalized = cv2.equalizeHist(resized)
    edges = cv2.Canny(equalized, 60, 140)
    return ProcessedImage(gray=equalized, edges=edges)
