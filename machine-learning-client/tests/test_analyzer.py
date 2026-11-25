"""Tests for image analysis and focus scoring."""

import cv2
import numpy as np
import pytest

from app import analyzer


@pytest.mark.parametrize("name", [analyzer.FACE_CASCADE, analyzer.EYE_CASCADE])
def test_bundled_cascades_load(name):
    """The cascade files exist in the installed OpenCV package."""
    assert not analyzer.load_cascade(name).empty()


@pytest.mark.parametrize("extension", [".png", ".jpg"])
def test_decode_image_returns_grayscale(extension):
    """PNG and JPEG bytes decode to a two-dimensional image."""
    data = cv2.imencode(extension, np.zeros((20, 30, 3), np.uint8))[1].tobytes()
    assert analyzer.decode_image(data).shape == (20, 30)


@pytest.mark.parametrize("data", [b"", b"not an image"])
def test_decode_image_rejects_invalid_bytes(data):
    """Empty and undecodable bytes raise ValueError."""
    with pytest.raises(ValueError):
        analyzer.decode_image(data)


def test_decode_image_converts_opencv_errors(monkeypatch):
    """Errors raised by OpenCV become ValueError."""

    def fail(*_args):
        raise cv2.error("bad data")  # pylint: disable=not-callable

    monkeypatch.setattr(analyzer.cv2, "imdecode", fail)
    with pytest.raises(ValueError):
        analyzer.decode_image(b"data")


def test_blank_image_has_no_face(blank_image):
    """The real cascades find nothing in a blank image."""
    assert analyzer.analyze_image(blank_image) == {
        "face_detected": False,
        "eyes_detected": False,
    }


@pytest.mark.parametrize(
    "eyes, expected", [([], False), ([(1, 1, 5, 5), (9, 1, 5, 5)], True)]
)
def test_face_with_and_without_eyes(monkeypatch, blank_image, eyes, expected):
    """Eyes are reported only when the eye cascade finds some."""
    monkeypatch.setattr(analyzer, "detect_faces", lambda image: [(0, 0, 50, 50)])
    monkeypatch.setattr(analyzer, "detect_eyes", lambda face: eyes)
    assert analyzer.analyze_image(blank_image) == {
        "face_detected": True,
        "eyes_detected": expected,
    }


def test_eyes_are_searched_in_upper_half_of_largest_face(monkeypatch, blank_image):
    """Smaller faces and the lower half of the face are ignored."""
    shapes = []
    monkeypatch.setattr(
        analyzer, "detect_faces", lambda image: [(0, 0, 10, 10), (20, 20, 60, 40)]
    )
    monkeypatch.setattr(
        analyzer, "detect_eyes", lambda face: shapes.append(face.shape) or []
    )
    analyzer.analyze_image(blank_image)
    assert shapes == [(20, 60)]


@pytest.mark.parametrize(
    "face, eyes, expected",
    [
        (False, False, 0),
        (False, True, 0),
        (True, False, 40),
        (True, True, 100),
    ],
)
def test_focus_score(face, eyes, expected):
    """The score depends on whether a face and eyes were found."""
    assert analyzer.focus_score(face, eyes) == expected
