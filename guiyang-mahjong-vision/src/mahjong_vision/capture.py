from dataclasses import dataclass

import mss
import numpy as np
import win32gui

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


@dataclass
class WindowCapture:
    title: str

    def __post_init__(self) -> None:
        self._screen = mss.mss()

    def capture(self) -> np.ndarray:
        handle = win32gui.FindWindow(None, self.title)
        if not handle or win32gui.IsIconic(handle):
            raise WindowUnavailable(f"window is unavailable: {self.title}")

        left, top, right, bottom = win32gui.GetWindowRect(handle)
        width = right - left
        height = bottom - top
        if width <= 0 or height <= 0:
            raise WindowUnavailable(f"window has invalid bounds: {self.title}")

        shot = self._screen.grab(
            {
                "left": left,
                "top": top,
                "width": width,
                "height": height,
            }
        )
        return np.asarray(shot)
