from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk

import numpy as np

from mahjong_vision.domain import ALL_TILES
from mahjong_vision.templates import TemplateStore


@dataclass(frozen=True)
class CalibrationRequest:
    slot_image: np.ndarray
    slot_index: int


class CalibrationDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        store: TemplateStore,
        slot_image: np.ndarray,
        slot_index: int,
    ) -> None:
        super().__init__(parent)
        self.title(f"标注第 {slot_index + 1} 张牌")
        self.attributes("-topmost", True)
        self.resizable(False, False)
        self.store = store
        self.slot_image = slot_image.copy()
        self.label_by_name = {tile.display_name: tile.label for tile in ALL_TILES}
        self.choice = tk.StringVar(value=ALL_TILES[0].display_name)

        ttk.Label(self, text=f"低置信度牌槽：{slot_index + 1}").pack(
            padx=12,
            pady=(12, 4),
        )
        ttk.Combobox(
            self,
            textvariable=self.choice,
            values=list(self.label_by_name),
            state="readonly",
            width=12,
        ).pack(padx=12, pady=4)
        ttk.Button(self, text="保存模板", command=self._save).pack(
            padx=12,
            pady=(4, 12),
        )

    def _save(self) -> None:
        self.store.add(self.label_by_name[self.choice.get()], self.slot_image)
        self.destroy()
