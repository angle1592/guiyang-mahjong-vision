import numpy as np
import pytest
import pywintypes
from mss.exception import ScreenShotError

from mahjong_vision import capture
from mahjong_vision.capture import (
    WindowCapture,
    WindowUnavailable,
    crop_slots,
    detect_hand_slots,
    slot_has_tile,
)
from mahjong_vision.config import HandConfig


class FakeScreen:
    def __init__(self, shot=None, grab_error=None):
        self.shot = (
            np.full((6, 8, 4), 7, dtype=np.uint8)
            if shot is None
            else shot
        )
        self.grab_error = grab_error
        self.monitor = None
        self.close_calls = 0

    def grab(self, monitor):
        self.monitor = monitor
        if self.grab_error is not None:
            raise self.grab_error
        return self.shot

    def close(self):
        self.close_calls += 1


def patch_available_window(monkeypatch):
    monkeypatch.setattr(capture.win32gui, "FindWindow", lambda _class, _title: 42)
    monkeypatch.setattr(capture.win32gui, "IsIconic", lambda _handle: False)
    monkeypatch.setattr(
        capture.win32gui,
        "GetClientRect",
        lambda _handle: (0, 0, 8, 6),
    )
    monkeypatch.setattr(
        capture.win32gui,
        "ClientToScreen",
        lambda _handle, point: (100 + point[0], 200 + point[1]),
    )


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


def test_slot_has_tile_distinguishes_blank_and_real_slots():
    blank = np.full((103, 74, 4), 24, dtype=np.uint8)
    tile = blank.copy()
    tile[10:90, 8:66] = 240
    tile[14:86, 12:62] = 255

    assert not slot_has_tile(blank)
    assert slot_has_tile(tile)


def test_detect_hand_slots_finds_bright_bottom_tiles():
    frame = np.zeros((140, 260, 3), dtype=np.uint8)
    frame[:, :] = (20, 80, 80)
    for index, x in enumerate((5, 60, 115)):
        frame[25:130, x:x + 45] = 240
        frame[30:120, x + 4:x + 41] = 255 - index * 20

    slots = detect_hand_slots(frame)

    assert len(slots) == 3
    assert slots[0].shape[0] >= 90
    assert slots[0].shape[1] >= 40


def test_window_capture_grabs_the_wechat_window(monkeypatch):
    screen = FakeScreen()
    monkeypatch.setattr(capture.mss, "MSS", lambda: screen)
    patch_available_window(monkeypatch)

    frame = WindowCapture("微信").capture()

    assert screen.monitor == {
        "left": 100,
        "top": 200,
        "width": 8,
        "height": 6,
    }
    assert frame.shape == (6, 8, 4)
    assert frame.mean() == 7


def test_window_capture_context_closes_screen_once(monkeypatch):
    screen = FakeScreen()
    monkeypatch.setattr(capture.mss, "MSS", lambda: screen)

    with WindowCapture("微信") as window_capture:
        assert window_capture.title == "微信"

    assert screen.close_calls == 1
    window_capture.close()
    assert screen.close_calls == 1


@pytest.mark.parametrize(
    ("handle", "iconic"),
    [(0, False), (42, True)],
)
def test_window_capture_rejects_missing_or_minimized_window(
    monkeypatch,
    handle,
    iconic,
):
    monkeypatch.setattr(capture.mss, "MSS", FakeScreen)
    monkeypatch.setattr(
        capture.win32gui,
        "FindWindow",
        lambda _class, _title: handle,
    )
    monkeypatch.setattr(capture.win32gui, "IsIconic", lambda _handle: iconic)

    with pytest.raises(WindowUnavailable):
        WindowCapture("微信").capture()


def test_window_capture_rejects_invalid_window_bounds(monkeypatch):
    monkeypatch.setattr(capture.mss, "MSS", FakeScreen)
    monkeypatch.setattr(capture.win32gui, "FindWindow", lambda _class, _title: 42)
    monkeypatch.setattr(capture.win32gui, "IsIconic", lambda _handle: False)
    monkeypatch.setattr(
        capture.win32gui,
        "GetClientRect",
        lambda _handle: (0, 0, 0, 6),
    )
    monkeypatch.setattr(
        capture.win32gui,
        "ClientToScreen",
        lambda _handle, point: (100 + point[0], 200 + point[1]),
    )

    with pytest.raises(WindowUnavailable):
        WindowCapture("微信").capture()


def test_window_capture_converts_window_api_race(monkeypatch):
    error = pywintypes.error(1400, "GetClientRect", "Invalid window handle")
    monkeypatch.setattr(capture.mss, "MSS", FakeScreen)
    monkeypatch.setattr(capture.win32gui, "FindWindow", lambda _class, _title: 42)
    monkeypatch.setattr(capture.win32gui, "IsIconic", lambda _handle: False)

    def missing_window(_handle):
        raise error

    monkeypatch.setattr(capture.win32gui, "GetClientRect", missing_window)

    with pytest.raises(WindowUnavailable) as caught:
        WindowCapture("微信").capture()

    assert caught.value.__cause__ is error


def test_window_capture_converts_screenshot_failure(monkeypatch):
    error = ScreenShotError("grab failed")
    monkeypatch.setattr(
        capture.mss,
        "MSS",
        lambda: FakeScreen(grab_error=error),
    )
    patch_available_window(monkeypatch)

    with pytest.raises(WindowUnavailable) as caught:
        WindowCapture("微信").capture()

    assert caught.value.__cause__ is error


def test_window_capture_does_not_hide_programming_errors(monkeypatch):
    error = TypeError("unexpected grab result")
    monkeypatch.setattr(
        capture.mss,
        "MSS",
        lambda: FakeScreen(grab_error=error),
    )
    patch_available_window(monkeypatch)

    with pytest.raises(TypeError) as caught:
        WindowCapture("微信").capture()

    assert caught.value is error
