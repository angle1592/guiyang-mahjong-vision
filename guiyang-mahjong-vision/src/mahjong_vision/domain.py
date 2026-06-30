from dataclasses import dataclass


_SUITS = ("m", "p", "s")
_SUIT_NAMES = ("万", "筒", "条")
_NUMERALS = ("一", "二", "三", "四", "五", "六", "七", "八", "九")


@dataclass(frozen=True, order=True)
class Tile:
    index: int

    def __post_init__(self) -> None:
        if type(self.index) is not int or not 0 <= self.index <= 26:
            raise ValueError("tile index must be an integer from 0 to 26")

    @classmethod
    def from_label(cls, label: str) -> "Tile":
        if (
            not isinstance(label, str)
            or len(label) != 2
            or label[0] not in "123456789"
            or label[1] not in _SUITS
        ):
            raise ValueError("tile label must be one of 1m..9m, 1p..9p, 1s..9s")
        return cls(_SUITS.index(label[1]) * 9 + int(label[0]) - 1)

    @property
    def label(self) -> str:
        suit, rank = divmod(self.index, 9)
        return f"{rank + 1}{_SUITS[suit]}"

    @property
    def display_name(self) -> str:
        suit, rank = divmod(self.index, 9)
        return f"{_NUMERALS[rank]}{_SUIT_NAMES[suit]}"


ALL_TILES = tuple(Tile(index) for index in range(27))
