import numpy as np
import pytest

from mahjong_vision.domain import ALL_TILES, Tile
from mahjong_vision.image_ops import ProcessedImage, preprocess


@pytest.mark.parametrize(
    ("label", "index", "display_name"),
    [
        ("1m", 0, "一万"),
        ("9m", 8, "九万"),
        ("1p", 9, "一筒"),
        ("8p", 16, "八筒"),
        ("9p", 17, "九筒"),
        ("1s", 18, "一条"),
        ("9s", 26, "九条"),
    ],
)
def test_tile_mapping_round_trips(
    label: str, index: int, display_name: str
) -> None:
    tile = Tile.from_label(label)

    assert tile == Tile(index)
    assert tile.label == label
    assert tile.display_name == display_name


def test_all_tiles_contains_all_unique_suited_tiles_in_index_order() -> None:
    assert len(ALL_TILES) == 27
    assert len(set(ALL_TILES)) == 27
    assert ALL_TILES == tuple(Tile(index) for index in range(27))
    assert {tile.label for tile in ALL_TILES} == {
        f"{rank}{suit}" for suit in "mps" for rank in range(1, 10)
    }


@pytest.mark.parametrize(
    "label",
    [
        "",
        "0m",
        "10m",
        "1z",
        "m1",
        "1M",
        " 1m",
        "1m ",
        1,
        None,
    ],
)
def test_tile_from_label_rejects_invalid_labels(label: object) -> None:
    with pytest.raises(ValueError):
        Tile.from_label(label)  # type: ignore[arg-type]


@pytest.mark.parametrize("index", [-1, 27, 1.0, True, "1"])
def test_tile_rejects_invalid_indices(index: object) -> None:
    with pytest.raises(ValueError):
        Tile(index)  # type: ignore[arg-type]


def test_tile_is_immutable_and_orderable() -> None:
    assert Tile(0) < Tile(1)
    with pytest.raises((AttributeError, TypeError)):
        Tile(0).index = 1  # type: ignore[misc]


@pytest.mark.parametrize("channels", [None, 3, 4])
def test_preprocess_accepts_supported_image_formats(channels: int | None) -> None:
    gray = np.zeros((20, 30), dtype=np.uint8)
    gray[4:16, 5:25] = 255
    if channels is None:
        image = gray
    else:
        image = np.repeat(gray[:, :, np.newaxis], channels, axis=2)

    result = preprocess(image, (15, 10))

    assert isinstance(result, ProcessedImage)
    assert result.gray.shape == (10, 15)
    assert result.edges.shape == (10, 15)
    assert result.gray.dtype == np.uint8
    assert result.edges.dtype == np.uint8
    assert np.count_nonzero(result.edges) > 0


def test_preprocess_is_deterministic() -> None:
    image = np.arange(24 * 32, dtype=np.uint8).reshape(24, 32)

    first = preprocess(image, (12, 8))
    second = preprocess(image.copy(), (12, 8))

    assert np.array_equal(first.gray, second.gray)
    assert np.array_equal(first.edges, second.edges)


def test_processed_image_equality_uses_identity() -> None:
    gray = np.zeros((2, 2), dtype=np.uint8)
    first = ProcessedImage(gray=gray, edges=gray.copy())
    second = ProcessedImage(gray=gray.copy(), edges=gray.copy())

    assert first == first
    assert first != second


@pytest.mark.parametrize("channels", [None, 3])
def test_preprocess_accepts_float_grayscale_and_bgr(
    channels: int | None,
) -> None:
    gray = np.linspace(0.0, 1.0, 24, dtype=np.float64).reshape(4, 6)
    image = gray if channels is None else np.repeat(gray[:, :, None], channels, axis=2)
    uint8_gray = (gray * 255).astype(np.uint8)
    uint8_image = (
        uint8_gray
        if channels is None
        else np.repeat(uint8_gray[:, :, None], channels, axis=2)
    )

    result = preprocess(image, (6, 4))
    expected = preprocess(uint8_image, (6, 4))

    assert result.gray.dtype == np.uint8
    assert result.edges.dtype == np.uint8
    assert result.gray.shape == (4, 6)
    assert np.array_equal(result.gray, expected.gray)
    assert np.array_equal(result.edges, expected.edges)


def test_preprocess_clips_wide_integers_before_processing() -> None:
    image = np.array([[-100, 0], [255, 10_000]], dtype=np.int32)
    clipped = np.array([[0, 0], [255, 255]], dtype=np.uint8)

    actual = preprocess(image, (2, 2))
    expected = preprocess(clipped, (2, 2))

    assert np.array_equal(actual.gray, expected.gray)
    assert np.array_equal(actual.edges, expected.edges)


def test_preprocess_clips_floats_to_normalized_domain_before_scaling() -> None:
    image = np.array([[-1e-7, 0.0], [0.5, 1.0001]], dtype=np.float64)
    normalized = np.array([[0, 0], [127, 255]], dtype=np.uint8)

    actual = preprocess(image, (2, 2))
    expected = preprocess(normalized, (2, 2))

    assert np.array_equal(actual.gray, expected.gray)
    assert np.array_equal(actual.edges, expected.edges)


@pytest.mark.parametrize(
    "image",
    [
        np.zeros((2, 2), dtype=np.bool_),
        np.full((2, 2), "1", dtype="<U1"),
        np.full((2, 2), object(), dtype=object),
        np.zeros((2, 2), dtype=np.complex64),
        np.zeros((2, 2), dtype="datetime64[D]"),
        np.zeros((2, 2), dtype="timedelta64[D]"),
    ],
)
def test_preprocess_rejects_unsupported_dtypes(image: np.ndarray) -> None:
    with pytest.raises(ValueError):
        preprocess(image, (2, 2))


@pytest.mark.parametrize("invalid_value", [np.nan, np.inf, -np.inf])
def test_preprocess_rejects_non_finite_floats(invalid_value: float) -> None:
    image = np.zeros((2, 2, 3), dtype=np.float32)
    image[0, 0, 0] = invalid_value

    with pytest.raises(ValueError):
        preprocess(image, (2, 2))


@pytest.mark.parametrize(
    "image",
    [
        np.array([], dtype=np.uint8),
        np.empty((0, 3), dtype=np.uint8),
        np.empty((2, 0, 3), dtype=np.uint8),
        np.zeros((2,), dtype=np.uint8),
        np.zeros((2, 3, 1), dtype=np.uint8),
        np.zeros((2, 3, 2), dtype=np.uint8),
        np.zeros((2, 3, 5), dtype=np.uint8),
        np.zeros((1, 2, 3, 4), dtype=np.uint8),
    ],
)
def test_preprocess_rejects_empty_or_unsupported_image_shapes(
    image: np.ndarray,
) -> None:
    with pytest.raises(ValueError):
        preprocess(image, (10, 10))


@pytest.mark.parametrize(
    "size",
    [
        (0, 1),
        (1, 0),
        (-1, 1),
        (1, -1),
        (True, 1),
        (1, False),
        (1.0, 1),
        (1, 1.0),
        ("1", 1),
        (1,),
        (1, 2, 3),
    ],
)
def test_preprocess_rejects_invalid_sizes(size: object) -> None:
    with pytest.raises(ValueError):
        preprocess(np.zeros((2, 2), dtype=np.uint8), size)  # type: ignore[arg-type]
