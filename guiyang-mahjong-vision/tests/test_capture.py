import numpy as np
import pytest

from mahjong_vision import capture
from mahjong_vision.capture import WindowCapture, WindowUnavailable, crop_slots
from mahjong_vision.config import HandConfig


def test_crop_slots_uses_fixed_stride_and_returns_copies():
    frame = np.zeros((5, 9, 3), dtype=np.uint8)
    frame[1:4, 1:3] = 10
    frame[1:4, 4:6] = 20
    expected_first = frame[1:4, 1:3].copy()
    expected_second = frame[1:4, 4:6].copy()
    hand = HandConfig(
        x=1,
        y=1,
        slot_width=2,
        slot_height=3,
        stride=3,
        count=2,
    )

    slots = crop_slots(frame, hand)

    assert len(slots) == 2
    assert slots[0].shape == (3, 2, 3)
    assert slots[1].shape == (3, 2, 3)
    np.testing.assert_array_equal(slots[0], expected_first)
    np.testing.assert_array_equal(slots[1], expected_second)
    frame[1:4, 1:3] = 99
    np.testing.assert_array_equal(slots[0], expected_first)


def test_crop_slots_rejects_slot_outside_frame():
    frame = np.zeros((5, 9, 3), dtype=np.uint8)
    hand = HandConfig(
        x=6,
        y=1,
        slot_width=2,
        slot_height=3,
        stride=2,
        count=2,
    )

    with pytest.raises(ValueError, match="outside"):
        crop_slots(frame, hand)


def test_window_capture_grabs_the_wechat_window(monkeypatch):
    class FakeScreen:
        def __init__(self):
            self.monitor = None

        def grab(self, monitor):
            self.monitor = monitor
            return np.full((6, 8, 4), 7, dtype=np.uint8)

    screen = FakeScreen()
    monkeypatch.setattr(capture.mss, "mss", lambda: screen)
    monkeypatch.setattr(capture.win32gui, "FindWindow", lambda _class, _title: 42)
    monkeypatch.setattr(capture.win32gui, "IsIconic", lambda _handle: False)
    monkeypatch.setattr(
        capture.win32gui,
        "GetWindowRect",
        lambda _handle: (100, 200, 108, 206),
    )

    frame = WindowCapture("微信").capture()

    assert screen.monitor == {
        "left": 100,
        "top": 200,
        "width": 8,
        "height": 6,
    }
    assert frame.shape == (6, 8, 4)
    assert frame.mean() == 7


@pytest.mark.parametrize(
    ("handle", "iconic"),
    [(0, False), (42, True)],
)
def test_window_capture_rejects_missing_or_minimized_window(
    monkeypatch,
    handle,
    iconic,
):
    monkeypatch.setattr(capture.mss, "mss", lambda: object())
    monkeypatch.setattr(
        capture.win32gui,
        "FindWindow",
        lambda _class, _title: handle,
    )
    monkeypatch.setattr(capture.win32gui, "IsIconic", lambda _handle: iconic)

    with pytest.raises(WindowUnavailable):
        WindowCapture("微信").capture()


def test_window_capture_rejects_invalid_window_bounds(monkeypatch):
    monkeypatch.setattr(capture.mss, "mss", lambda: object())
    monkeypatch.setattr(capture.win32gui, "FindWindow", lambda _class, _title: 42)
    monkeypatch.setattr(capture.win32gui, "IsIconic", lambda _handle: False)
    monkeypatch.setattr(
        capture.win32gui,
        "GetWindowRect",
        lambda _handle: (100, 200, 100, 206),
    )

    with pytest.raises(WindowUnavailable):
        WindowCapture("微信").capture()
