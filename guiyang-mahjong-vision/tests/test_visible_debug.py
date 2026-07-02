from dataclasses import dataclass
import json

import numpy as np

from mahjong_vision.config import VisibleRegionConfig, VisibleRegionsConfig
from mahjong_vision.templates import MatchResult
from mahjong_vision.visible_debug import write_visible_debug_capture


@dataclass
class FakeStore:
    results: list[MatchResult]

    def match(self, image: np.ndarray) -> MatchResult:
        assert image.size
        return self.results.pop(0)


def region(x=0, y=0, count=1) -> VisibleRegionConfig:
    return VisibleRegionConfig(
        x=x,
        y=y,
        slot_width=4,
        slot_height=5,
        stride=6,
        count=count,
    )


def accepted(label: str) -> MatchResult:
    return MatchResult(label=label, score=0.95, runner_up_score=0.1, accepted=True)


def rejected(label: str | None = None) -> MatchResult:
    return MatchResult(label=label, score=0.4, runner_up_score=0.39, accepted=False)


def read_report(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_debug_capture_writes_frame_slots_and_report(tmp_path):
    frame = np.zeros((30, 40, 3), dtype=np.uint8)
    regions = VisibleRegionsConfig(
        discards=(region(count=2),),
        melds=(region(y=6, count=3),),
        revealed=(region(y=12, count=1),),
    )
    store = FakeStore(
        [
            accepted("1m"),
            rejected(),
            accepted("3p"),
            accepted("3p"),
            accepted("3p"),
            accepted("8s"),
        ]
    )

    report_path = write_visible_debug_capture(
        frame=frame,
        regions=regions,
        store=store,
        output_dir=tmp_path,
    )
    report = read_report(report_path)

    assert report_path == tmp_path / "visible-report.json"
    assert (tmp_path / "frame.png").exists()
    assert (tmp_path / "discards_0_slot_00.png").exists()
    assert (tmp_path / "discards_0_slot_01.png").exists()
    assert (tmp_path / "melds_0_slot_00.png").exists()
    assert (tmp_path / "revealed_0_slot_00.png").exists()
    assert report["summary"] == {"total_slots": 6, "accepted_slots": 5}
    assert report["discards"][0] == {
        "region": 0,
        "slot": 0,
        "image": "discards_0_slot_00.png",
        "label": "1m",
        "accepted": True,
        "score": 0.95,
        "runner_up_score": 0.1,
    }
    assert report["discards"][1]["accepted"] is False
    assert report["melds"][0]["image"] == "melds_0_slot_00.png"
    assert report["revealed"][0]["label"] == "8s"


def test_debug_capture_allows_empty_visible_regions(tmp_path):
    frame = np.zeros((8, 8, 3), dtype=np.uint8)
    regions = VisibleRegionsConfig(discards=(), melds=(), revealed=())

    report_path = write_visible_debug_capture(
        frame=frame,
        regions=regions,
        store=FakeStore([]),
        output_dir=tmp_path,
    )
    report = read_report(report_path)

    assert (tmp_path / "frame.png").exists()
    assert report["discards"] == []
    assert report["melds"] == []
    assert report["revealed"] == []
    assert report["summary"] == {"total_slots": 0, "accepted_slots": 0}


def test_debug_capture_uses_stable_region_and_slot_names(tmp_path):
    frame = np.zeros((20, 40, 3), dtype=np.uint8)
    regions = VisibleRegionsConfig(
        discards=(region(count=1), region(y=6, count=2)),
        melds=(),
        revealed=(),
    )
    store = FakeStore([accepted("1m"), accepted("2m"), accepted("3m")])

    report_path = write_visible_debug_capture(
        frame=frame,
        regions=regions,
        store=store,
        output_dir=tmp_path,
    )
    report = read_report(report_path)

    assert [entry["image"] for entry in report["discards"]] == [
        "discards_0_slot_00.png",
        "discards_1_slot_00.png",
        "discards_1_slot_01.png",
    ]


def test_debug_capture_cleans_stale_generated_outputs_without_touching_user_files(
    tmp_path,
):
    frame = np.zeros((20, 40, 3), dtype=np.uint8)
    first_regions = VisibleRegionsConfig(
        discards=(region(count=3),),
        melds=(),
        revealed=(),
    )
    second_regions = VisibleRegionsConfig(
        discards=(region(count=1),),
        melds=(),
        revealed=(),
    )

    write_visible_debug_capture(
        frame=frame,
        regions=first_regions,
        store=FakeStore([accepted("1m"), accepted("2m"), accepted("3m")]),
        output_dir=tmp_path,
    )
    (tmp_path / "notes.txt").write_text("keep", encoding="utf-8")
    (tmp_path / "custom_slot_99.png").write_bytes(b"keep")

    write_visible_debug_capture(
        frame=frame,
        regions=second_regions,
        store=FakeStore([accepted("4m")]),
        output_dir=tmp_path,
    )
    report = read_report(tmp_path / "visible-report.json")

    assert (tmp_path / "discards_0_slot_00.png").exists()
    assert not (tmp_path / "discards_0_slot_01.png").exists()
    assert not (tmp_path / "discards_0_slot_02.png").exists()
    assert (tmp_path / "notes.txt").read_text(encoding="utf-8") == "keep"
    assert (tmp_path / "custom_slot_99.png").read_bytes() == b"keep"
    assert [entry["image"] for entry in report["discards"]] == [
        "discards_0_slot_00.png"
    ]
