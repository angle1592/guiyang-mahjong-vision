from dataclasses import dataclass

import mss
import numpy as np
import cv2
import pywintypes
import win32gui
from mss.exception import ScreenShotError

from mahjong_vision.config import HandConfig


class WindowUnavailable(RuntimeError):
    pass


def crop_slots(
    frame: np.ndarray,
    hand: HandConfig,
) -> tuple[np.ndarray, ...]:
    frame_height, frame_width = frame.shape[:2]
    slots = []
    for rect in hand.slot_rects():
        right = rect.x + rect.width
        bottom = rect.y + rect.height
        if (
            rect.x < 0
            or rect.y < 0
            or right > frame_width
            or bottom > frame_height
        ):
            raise ValueError("hand slot is outside the frame")
        slots.append(frame[rect.y:bottom, rect.x:right].copy())
    return tuple(slots)


def slot_has_tile(slot: np.ndarray) -> bool:
    if slot.ndim == 3:
        gray = slot[:, :, :3].mean(axis=2)
    else:
        gray = slot
    return float(gray.std()) > 20.0 and float((gray > 180).mean()) > 0.02


def detect_hand_slots(frame: np.ndarray) -> tuple[np.ndarray, ...]:
    bottom = frame[max(0, frame.shape[0] - 160):, :, :3]
    gray = cv2.cvtColor(bottom, cv2.COLOR_BGR2GRAY)
    _, threshold = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)
    count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(
        threshold,
        8,
    )
    boxes: list[tuple[int, int, int, int]] = []
    for index in range(1, count):
        x, y, width, height, area = stats[index]
        if width > 120 and height > 70:
            slot_count = max(1, round(width / 78))
            slot_width = width / slot_count
            for slot_index in range(slot_count):
                left = int(round(x + slot_index * slot_width))
                right = int(round(x + (slot_index + 1) * slot_width))
                if right - left > 40:
                    boxes.append((left, int(y), right - left, int(height)))
            continue
        if area > 1000 and width > 40 and height > 70:
            boxes.append((int(x), int(y), int(width), int(height)))
    boxes.sort()
    return tuple(bottom[y:y + height, x:x + width].copy() for x, y, width, height in boxes)


@dataclass
class WindowCapture:
    title: str

    def __post_init__(self) -> None:
        self._screen = mss.MSS()

    def close(self) -> None:
        if self._screen is not None:
            screen = self._screen
            self._screen = None
            screen.close()

    def __enter__(self) -> "WindowCapture":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def capture(self) -> np.ndarray:
        try:
            handle = win32gui.FindWindow(None, self.title)
            if not handle or win32gui.IsIconic(handle):
                raise WindowUnavailable(f"window is unavailable: {self.title}")
            left, top, right, bottom = win32gui.GetClientRect(handle)
            left, top = win32gui.ClientToScreen(handle, (left, top))
            right, bottom = win32gui.ClientToScreen(handle, (right, bottom))
        except pywintypes.error as error:
            raise WindowUnavailable(
                f"window is unavailable: {self.title}"
            ) from error

        width = right - left
        height = bottom - top
        if width <= 0 or height <= 0:
            raise WindowUnavailable(f"window has invalid bounds: {self.title}")

        try:
            shot = self._screen.grab(
                {
                    "left": left,
                    "top": top,
                    "width": width,
                    "height": height,
                }
            )
        except ScreenShotError as error:
            raise WindowUnavailable(
                f"could not capture window: {self.title}"
            ) from error
        return np.asarray(shot)
