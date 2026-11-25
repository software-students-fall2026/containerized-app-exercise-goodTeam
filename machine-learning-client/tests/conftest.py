"""Shared fixtures for the ML client tests."""

import cv2
import mongomock
import numpy as np
import pytest

from app.main import create_app


@pytest.fixture(name="database")
def database_fixture():
    """Return an in-memory Mongo database."""
    return mongomock.MongoClient().db


@pytest.fixture(name="client")
def client_fixture(database):
    """Return a Flask test client backed by the in-memory database."""
    return create_app(database).test_client()


@pytest.fixture(name="blank_image")
def blank_image_fixture():
    """Return the PNG bytes of a blank image."""
    return cv2.imencode(".png", np.zeros((100, 100), np.uint8))[1].tobytes()
