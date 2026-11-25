"""Tests for the frame and session endpoints."""

from datetime import datetime, timezone
from io import BytesIO
from types import SimpleNamespace

import pytest
import requests

from app import main


@pytest.fixture(name="app")
def app_fixture(database, monkeypatch):
    """Return the app with a fixed ML client URL."""
    monkeypatch.setenv("ML_CLIENT_URL", "http://ml:8000")
    return main.create_app(database)


def mock_post(monkeypatch, status_code=200, payload=None, error=None):
    """Replace requests.post and return a list that records its calls."""
    calls = []

    def json():
        if payload is None:
            raise ValueError("not json")
        return payload

    def post(url, data, files, timeout):
        image = files["image"] if files else None
        calls.append(
            {
                "url": url,
                "data": data,
                "image": image and (image[0], image[1].read(), image[2]),
                "timeout": timeout,
            }
        )
        if error:
            raise error
        return SimpleNamespace(status_code=status_code, json=json)

    monkeypatch.setattr(main.requests, "post", post)
    return calls


def post_frame(client):
    """Post a sample frame to the web app."""
    return client.post(
        "/frame",
        data={"session_id": "s1", "image": (BytesIO(b"jpeg"), "f.jpg", "image/jpeg")},
    )


def add_frame(database, session_id, second, score):
    """Insert an analyzed frame at the given second."""
    database.frames.insert_one(
        {
            "session_id": session_id,
            "ts": datetime(2026, 1, 1, 12, 0, second, tzinfo=timezone.utc),
            "face_detected": score > 0,
            "eyes_detected": score == 100,
            "focus_score": score,
        }
    )


def test_frame_forwards_upload(client, monkeypatch):
    """The upload reaches the ML client and its JSON is returned."""
    payload = {"face_detected": True, "eyes_detected": True, "focus_score": 100}
    calls = mock_post(monkeypatch, payload=payload)

    response = post_frame(client)

    assert response.status_code == 200
    assert response.get_json() == payload
    assert calls == [
        {
            "url": "http://ml:8000/analyze",
            "data": {"session_id": "s1"},
            "image": ("f.jpg", b"jpeg", "image/jpeg"),
            "timeout": 10,
        }
    ]


def test_frame_passes_on_validation_errors(client, monkeypatch):
    """A 400 from the ML client is returned unchanged."""
    calls = mock_post(monkeypatch, 400, {"error": "image is required"})

    response = client.post("/frame", data={"session_id": "s1"})

    assert response.status_code == 400
    assert response.get_json() == {"error": "image is required"}
    assert calls[0]["image"] is None


@pytest.mark.parametrize(
    "reply",
    [
        {"error": requests.ConnectionError("down")},
        {"error": requests.Timeout("slow")},
        {"status_code": 500, "payload": {"error": "crash"}},
        {"status_code": 200, "payload": None},
    ],
)
def test_frame_returns_502_when_ml_client_fails(client, monkeypatch, reply):
    """Connection failures, server errors and non-JSON replies become 502."""
    mock_post(monkeypatch, **reply)

    response = post_frame(client)

    assert response.status_code == 502
    assert "error" in response.get_json()


def test_session_empty(client):
    """An unknown session has no frames and a zero summary."""
    response = client.get("/api/sessions/missing")

    assert response.status_code == 200
    assert response.get_json() == {
        "frames": [],
        "summary": {"count": 0, "avg_focus": 0, "focused_pct": 0},
    }


def test_session_one_frame(client, database):
    """A single frame is returned with a UTC timestamp."""
    add_frame(database, "s1", 1, 100)

    assert client.get("/api/sessions/s1").get_json() == {
        "frames": [{"ts": "2026-01-01T12:00:01.000+00:00", "focus_score": 100}],
        "summary": {"count": 1, "avg_focus": 100, "focused_pct": 100},
    }


def test_session_several_frames(client, database):
    """Frames are sorted by time, and other sessions are left out."""
    add_frame(database, "s1", 3, 100)
    add_frame(database, "s1", 1, 0)
    add_frame(database, "s1", 2, 40)
    add_frame(database, "other", 4, 100)

    body = client.get("/api/sessions/s1").get_json()

    assert [frame["focus_score"] for frame in body["frames"]] == [0, 40, 100]
    assert body["summary"] == {"count": 3, "avg_focus": 46.7, "focused_pct": 33.3}
