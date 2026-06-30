from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class ProcessedImage:
    gray: np.ndarray
    edges: np.ndarray


def preprocess(image: np.ndarray, size: tuple[int, int]) -> ProcessedImage:
    if (
        not isinstance(size, tuple)
        or len(size) != 2
        or any(type(dimension) is not int or dimension <= 0 for dimension in size)
    ):
        raise ValueError("size must be a (width, height) tuple of positive integers")
    if not isinstance(image, np.ndarray) or image.size == 0:
        raise ValueError("image must be a non-empty numpy array")

    if image.ndim == 2:
        gray = image
    elif image.ndim == 3 and image.shape[2] == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    elif image.ndim == 3 and image.shape[2] == 4:
        gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    else:
        raise ValueError("image must be grayscale, BGR, or BGRA")

    if gray.dtype != np.uint8:
        gray = np.clip(gray, 0, 255).astype(np.uint8)
    resized = cv2.resize(gray, size, interpolation=cv2.INTER_AREA)
    equalized = cv2.equalizeHist(resized)
    edges = cv2.Canny(equalized, 60, 140)
    return ProcessedImage(gray=equalized, edges=edges)
