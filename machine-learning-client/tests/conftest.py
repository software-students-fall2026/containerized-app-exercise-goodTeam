"""Shared fixtures for the ML client tests."""

import mongomock
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
