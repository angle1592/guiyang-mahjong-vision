from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import Event

import cv2
import numpy as np
import pytest

from mahjong_vision.templates import MatchResult, TemplateStore


SIZE = (48, 64)


def tile_image(rank: int, suit: int = 0) -> np.ndarray:
    image = np.full((96, 72, 3), 245, dtype=np.uint8)
    cv2.rectangle(image, (4, 4), (67, 91), (20, 20, 20), 2)
    cv2.putText(
        image,
        str(rank),
        (18, 52),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.45,
        (15, 15, 15),
        3,
        cv2.LINE_AA,
    )
    cv2.line(image, (12, 70 + suit * 4), (60, 70 + suit * 4), (30, 30, 30), 3)
    return image


def test_empty_store_rejects_match(tmp_path):
    store = TemplateStore(tmp_path, SIZE, threshold=0.8, min_margin=0.1)

    assert store.match(tile_image(1)) == MatchResult(None, 0.0, 0.0, False)


def test_constructor_normalizes_size_and_validates_thresholds(tmp_path):
    store = TemplateStore(tmp_path, [48, 64], threshold=0, min_margin=1)

    assert store.root == tmp_path
    assert store.size == SIZE
    with pytest.raises(ValueError):
        TemplateStore(tmp_path, SIZE, threshold=-0.01, min_margin=0.1)
    with pytest.raises(ValueError):
        TemplateStore(tmp_path, SIZE, threshold=0.8, min_margin=1.01)


def test_constructor_accepts_positional_matching_thresholds(tmp_path):
    store = TemplateStore(tmp_path, SIZE, 0.8, 0.05)

    assert store.threshold == 0.8
    assert store.min_margin == 0.05


def test_add_persists_and_reload_recognizes_sample(tmp_path):
    image = tile_image(3)
    store = TemplateStore(tmp_path, SIZE, threshold=0.8, min_margin=0.05)

    saved = store.add("3m", image)

    assert saved.parent == tmp_path / "3m"
    assert saved.suffix == ".png"
    assert saved.is_file()
    reloaded = TemplateStore(tmp_path, SIZE, threshold=0.8, min_margin=0.05)
    reloaded.reload()
    result = reloaded.match(image)
    assert result.label == "3m"
    assert result.score == pytest.approx(1.0, abs=1e-6)
    assert result.runner_up_score == 0.0
    assert result.accepted


def test_constructor_loads_existing_templates(tmp_path):
    writer = TemplateStore(tmp_path, SIZE, threshold=0.8, min_margin=0.05)
    writer.add("3m", tile_image(3))

    reader = TemplateStore(tmp_path, SIZE, threshold=0.8, min_margin=0.05)

    assert reader.match(tile_image(3)).label == "3m"


def test_match_ranks_distinct_labels(tmp_path):
    store = TemplateStore(tmp_path, SIZE, threshold=0.7, min_margin=0.05)
    store.add("2m", tile_image(2))
    store.add("8p", tile_image(8, suit=1))

    result = store.match(tile_image(8, suit=1))

    assert result.label == "8p"
    assert result.score > result.runner_up_score
    assert result.accepted


def test_ambiguous_blank_templates_are_rejected(tmp_path):
    blank = np.full((96, 72), 255, dtype=np.uint8)
    store = TemplateStore(tmp_path, SIZE, threshold=0.8, min_margin=0.05)
    store.add("1m", blank)
    store.add("2m", blank)

    result = store.match(blank)

    assert result.label == "1m"
    assert result.score == pytest.approx(result.runner_up_score)
    assert not result.accepted


def test_featureless_template_is_rejected(tmp_path):
    blank = np.full((96, 72), 255, dtype=np.uint8)
    store = TemplateStore(tmp_path, SIZE, threshold=0.8, min_margin=0.05)
    store.add("1m", blank)

    result = store.match(blank)

    assert result.score == 0.0
    assert not result.accepted


def test_add_rejects_invalid_label_and_image(tmp_path):
    store = TemplateStore(tmp_path, SIZE, threshold=0.8, min_margin=0.05)

    with pytest.raises(ValueError):
        store.add("east", tile_image(1))
    with pytest.raises(ValueError):
        store.add("1m", np.array([], dtype=np.uint8))

    assert not tmp_path.exists() or not any(tmp_path.iterdir())


def test_reload_ignores_invalid_directories_and_unreadable_pngs(tmp_path):
    invalid_dir = tmp_path / "east"
    invalid_dir.mkdir(parents=True)
    cv2.imwrite(str(invalid_dir / "sample.png"), tile_image(1))
    valid_dir = tmp_path / "1m"
    valid_dir.mkdir()
    (valid_dir / "broken.png").write_text("not a PNG", encoding="utf-8")
    cv2.imwrite(str(valid_dir / "valid.png"), tile_image(1))

    store = TemplateStore(tmp_path, SIZE, threshold=0.8, min_margin=0.05)
    store.reload()

    assert store.match(tile_image(1)).label == "1m"
    assert not store.match(tile_image(9)).accepted


def test_failed_write_does_not_add_sample_to_memory(tmp_path, monkeypatch):
    store = TemplateStore(tmp_path, SIZE, threshold=0.8, min_margin=0.05)
    monkeypatch.setattr(cv2, "imwrite", lambda *_args, **_kwargs: False)

    with pytest.raises(OSError):
        store.add("4m", tile_image(4))

    assert store.match(tile_image(4)) == MatchResult(None, 0.0, 0.0, False)


def test_label_score_uses_best_of_multiple_samples(tmp_path):
    store = TemplateStore(tmp_path, SIZE, threshold=0.8, min_margin=0.05)
    store.add("5s", tile_image(1))
    store.add("5s", tile_image(5, suit=2))
    store.add("6s", tile_image(6, suit=2))

    result = store.match(tile_image(5, suit=2))

    assert result.label == "5s"
    assert result.score == pytest.approx(1.0, abs=1e-6)
    assert result.accepted


def test_concurrent_add_and_match_smoke(tmp_path):
    store = TemplateStore(tmp_path, SIZE, threshold=0.7, min_margin=0)
    images = [tile_image(rank) for rank in range(1, 7)]

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(store.add, f"{rank}m", image)
            for rank, image in enumerate(images, start=1)
        ]
        futures.extend(executor.submit(store.match, image) for image in images * 2)
        for future in futures:
            future.result()

    for rank, image in enumerate(images, start=1):
        assert store.match(image).label == f"{rank}m"


def test_reload_does_not_overwrite_concurrent_add(tmp_path, monkeypatch):
    store = TemplateStore(tmp_path, SIZE, threshold=0.7, min_margin=0)
    store.add("1m", tile_image(1))
    reload_started = Event()
    allow_reload = Event()
    original_imread = cv2.imread

    def blocking_imread(*args, **kwargs):
        reload_started.set()
        assert allow_reload.wait(timeout=2)
        return original_imread(*args, **kwargs)

    monkeypatch.setattr(cv2, "imread", blocking_imread)
    with ThreadPoolExecutor(max_workers=2) as executor:
        reload_future = executor.submit(store.reload)
        assert reload_started.wait(timeout=2)
        add_future = executor.submit(store.add, "2m", tile_image(2))
        try:
            add_future.result(timeout=0.2)
        except TimeoutError:
            pass
        allow_reload.set()
        reload_future.result(timeout=2)
        add_future.result(timeout=2)

    assert store.match(tile_image(2)).label == "2m"
