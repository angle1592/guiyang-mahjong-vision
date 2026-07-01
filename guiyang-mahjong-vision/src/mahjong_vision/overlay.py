from __future__ import annotations

from dataclasses import dataclass
from queue import Empty, Queue
import tkinter as tk
from tkinter import ttk

from mahjong_vision.calibration import CalibrationDialog, CalibrationRequest
from mahjong_vision.templates import TemplateStore


@dataclass(frozen=True)
class OverlayState:
    status: str
    hand: str = ""
    recommendation: str = ""
    detail: str = ""


class Overlay:
    def __init__(
        self,
        updates: Queue[OverlayState],
        calibration_requests: Queue[CalibrationRequest],
        store: TemplateStore,
    ) -> None:
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
                anchor="w",
                padx=10,
                pady=2,
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
        if (
            self.calibration_dialog is not None
            and self.calibration_dialog.winfo_exists()
        ):
            self.root.after(50, self._drain_calibration)
            return

        self.calibration_dialog = None
        try:
            request = self.calibration_requests.get_nowait()
        except Empty:
            self.root.after(50, self._drain_calibration)
            return

        self.calibration_dialog = CalibrationDialog(
            self.root,
            self.store,
            request.slot_image,
            request.slot_index,
        )
        self.root.after(50, self._drain_calibration)

    def run(self) -> None:
        self.root.mainloop()
