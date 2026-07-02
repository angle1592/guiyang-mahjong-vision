from pathlib import Path
import sys

from mahjong_vision import app
from mahjong_vision.advisor import AdvisorWeights
from mahjong_vision.app import _state_for_live_recognition


def test_runtime_root_uses_project_root_when_not_frozen(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)

    assert app._runtime_root() == Path(app.__file__).resolve().parents[2]


def test_runtime_root_uses_executable_directory_when_frozen(
    monkeypatch,
    tmp_path,
):
    executable = tmp_path / "贵阳麻将识牌助手.exe"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))

    assert app._runtime_root() == tmp_path


def test_legal_slot_count_with_unknowns_does_not_claim_illegal_hand():
    state = _state_for_live_recognition(
        labels=(
            "2m",
            "8m",
            "9m",
            "3s",
            "5s",
            "1p",
            "4p",
            "4p",
            "4p",
        ),
        slot_count=11,
        unknown_count=2,
        elapsed_ms=107.0,
        weights=AdvisorWeights(2.0, 2.5, 0.4),
    )

    assert "不符合" not in state.recommendation
    assert "该出牌" in state.recommendation
    assert "检测到 11 张" in state.status
    assert "未识别 2" in state.detail


def test_before_draw_hand_does_not_show_discard_advice():
    state = _state_for_live_recognition(
        labels=(
            "4m",
            "5m",
            "6m",
            "4s",
            "5s",
            "6s",
            "7s",
            "8s",
            "2p",
            "4p",
            "6p",
            "8p",
            "8p",
        ),
        slot_count=13,
        unknown_count=0,
        elapsed_ms=20.0,
        weights=AdvisorWeights(2.0, 2.5, 0.4),
    )

    assert state.recommendation == "摸牌后再提示"
    assert "优先打" not in state.recommendation
    assert "等待出牌" in state.status
