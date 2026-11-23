"""Shared fixtures for the web app tests."""

import mongomock
import pytest

from app.main import create_app


@pytest.fixture(name="database")
def database_fixture():
    """Return an in-memory Mongo database."""
    return mongomock.MongoClient().db


@pytest.fixture(name="app")
def app_fixture(database):
    """Return the Flask app backed by the in-memory database (used by pytest-flask)."""
    return create_app(database)
