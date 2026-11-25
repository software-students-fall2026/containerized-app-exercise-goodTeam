"""Tests for the ML client app."""

from datetime import datetime
from io import BytesIO

import mongomock
import pytest

from app import main


def test_health_returns_ok(client):
    """The health endpoint reports ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_create_app_writes_nothing(client, database):
    """Creating the app does not add documents."""
    assert client is not None
    assert database.list_collection_names() == []


@pytest.mark.parametrize(
    "face, eyes, score", [(False, False, 0), (True, False, 40), (True, True, 100)]
)
def test_analyze_returns_and_saves_result(
    client, database, monkeypatch, face, eyes, score
):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    """A valid frame is scored, returned and saved without the image."""
    result = {"face_detected": face, "eyes_detected": eyes}
    monkeypatch.setattr(main, "analyze_image", lambda data: dict(result))

    response = client.post(
        "/analyze", data={"session_id": "s1", "image": (BytesIO(b"frame"), "f.jpg")}
    )

    assert response.status_code == 200
    body = response.get_json()
    timestamp = datetime.fromisoformat(body.pop("ts"))
    assert body == {**result, "focus_score": score}
    assert list(database.frames.find({}, {"_id": 0})) == [
        {"session_id": "s1", "ts": timestamp.replace(tzinfo=None), **body}
    ]


def test_analyze_blank_image(client, blank_image):
    """A blank image goes through real detection and scores zero."""
    response = client.post(
        "/analyze", data={"session_id": "s1", "image": (BytesIO(blank_image), "f.png")}
    )
    assert response.status_code == 200
    assert response.get_json()["focus_score"] == 0


@pytest.mark.parametrize("session_id", [None, "  "])
def test_analyze_requires_session_id(client, database, blank_image, session_id):
    """A missing or blank session_id returns 400 and saves nothing."""
    data = {"image": (BytesIO(blank_image), "f.png")}
    if session_id is not None:
        data["session_id"] = session_id
    response = client.post("/analyze", data=data)
    assert response.status_code == 400
    assert "session_id" in response.get_json()["error"]
    assert database.frames.count_documents({}) == 0


@pytest.mark.parametrize("image", [None, b"", b"not an image"])
def test_analyze_requires_valid_image(client, database, image):
    """A missing, empty or undecodable image returns 400 and saves nothing."""
    data = {"session_id": "s1"}
    if image is not None:
        data["image"] = (BytesIO(image), "f.png")
    response = client.post("/analyze", data=data)
    assert response.status_code == 400
    assert "image" in response.get_json()["error"]
    assert database.frames.count_documents({}) == 0


def test_get_database_uses_given_uri(monkeypatch):
    """The database name comes from the URI path."""

    # setting MongoClient to the mock
    monkeypatch.setattr(main, "MongoClient", mongomock.MongoClient)
    database = main.get_database("mongodb://localhost/testdb")
    assert database.name == "testdb"


def test_get_database_falls_back_to_env(monkeypatch):
    """Without an argument the URI is read from MONGO_URI."""
    monkeypatch.setattr(main, "MongoClient", mongomock.MongoClient)
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost/envdb")
    assert main.get_database().name == "envdb"


def test_create_app_connects_when_no_database_given(monkeypatch, database):
    """create_app uses get_database when no database is passed."""
    monkeypatch.setattr(main, "get_database", lambda: database)
    client = main.create_app().test_client()
    assert client.get("/health").status_code == 200
