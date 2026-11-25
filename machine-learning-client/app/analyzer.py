"""Face and eye detection using OpenCV Haar cascades, and focus scoring."""

from functools import lru_cache
from pathlib import Path
from threading import Lock

import cv2
import numpy as np

FACE_CASCADE = "haarcascade_frontalface_default.xml"
EYE_CASCADE = "haarcascade_eye.xml"

# Cascades are shared between Flask threads but are not thread-safe.
_cascade_lock = Lock()


@lru_cache(maxsize=None)
def load_cascade(name):
    """Load a cascade file bundled with OpenCV."""
    return cv2.CascadeClassifier(str(Path(cv2.data.haarcascades) / name))


def decode_image(data):
    """Decode image bytes to grayscale, raising ValueError if they are invalid."""
    if not data:
        raise ValueError("image is empty")
    try:
        image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_GRAYSCALE)
    except cv2.error:  # pylint: disable=catching-non-exception
        raise ValueError("image could not be decoded") from None
    if image is None:
        raise ValueError("image could not be decoded")
    return image


def detect(name, image):
    """Return the (x, y, width, height) boxes a cascade finds in an image."""
    with _cascade_lock:
        boxes = load_cascade(name).detectMultiScale(
            image, scaleFactor=1.1, minNeighbors=5
        )
    return [tuple(int(value) for value in box) for box in boxes]


def detect_faces(image):
    """Return the face boxes in a grayscale image."""
    return detect(FACE_CASCADE, image)


def detect_eyes(face):
    """Return the eye boxes in a grayscale face image."""
    return detect(EYE_CASCADE, face)


def analyze_image(data):
    """Return whether a face, and eyes within it, are present in image bytes."""
    image = decode_image(data)
    faces = detect_faces(image)
    if not faces:
        return {"face_detected": False, "eyes_detected": False}

    # The largest face is most likely the user. Eyes are in its upper half, so
    # skipping the rest avoids mistaking a mouth or nostrils for eyes.
    left, top, width, height = max(faces, key=lambda box: box[2] * box[3])
    upper_face = image[top : top + height // 2, left : left + width]
    return {"face_detected": True, "eyes_detected": bool(detect_eyes(upper_face))}


def focus_score(face, eyes):
    """Return 0 without a face, 40 for a face only, 100 for a face and eyes."""
    if not face:
        return 0
    return 100 if eyes else 40
