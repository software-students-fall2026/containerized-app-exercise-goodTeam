"""Tests for the web app."""

from datetime import datetime, timezone

import mongomock
import requests

from app import main


class FakeResponse:
    """Minimal stand-in for a requests response."""

    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error

    def json(self):
        """Return the payload or raise the configured error."""
        if self.error:
            raise self.error
        return self.payload


def add_document(database, message, minute):
    """Insert a hello document created at the given minute."""
    database.hello.insert_one(
        {
            "source": "ml-client",
            "message": message,
            "created_at": datetime(2026, 1, 1, 12, minute, tzinfo=timezone.utc),
        }
    )


def test_index_lists_documents_and_status(client, database, monkeypatch):
    """The page shows stored documents and the ML client status."""
    monkeypatch.setattr(main, "check_ml_client", lambda url: "ok")
    add_document(database, "first message", 1)

    response = client.get("/")

    assert response.status_code == 200
    assert b"first message" in response.data
    assert b"<strong>ok</strong>" in response.data


def test_index_shows_empty_state(client, monkeypatch):
    """The page says so when there are no documents."""
    monkeypatch.setattr(main, "check_ml_client", lambda url: "ok")

    response = client.get("/")

    assert b"No documents yet." in response.data


def test_index_orders_newest_first(client, database, monkeypatch):
    """Newer documents appear above older ones."""
    monkeypatch.setattr(main, "check_ml_client", lambda url: "ok")
    add_document(database, "older message", 1)
    add_document(database, "newer message", 2)

    body = client.get("/").data

    assert body.index(b"newer message") < body.index(b"older message")


def test_index_limits_to_ten_documents(client, database, monkeypatch):
    """Only the ten newest documents are listed."""
    monkeypatch.setattr(main, "check_ml_client", lambda url: "ok")
    for minute in range(12):
        add_document(database, f"message {minute:02d}", minute)

    body = client.get("/").data

    assert b"message 11" in body
    assert b"message 01" not in body


def test_check_ml_client_ok(monkeypatch):
    """A healthy ML client reports its status."""
    monkeypatch.setattr(
        main.requests, "get", lambda url, timeout: FakeResponse({"status": "ok"})
    )
    assert main.check_ml_client("http://ml") == "ok"


def test_check_ml_client_requests_health_endpoint(monkeypatch):
    """The health endpoint of the given URL is called."""
    calls = []

    def fake_get(url, timeout):
        calls.append((url, timeout))
        return FakeResponse({"status": "ok"})

    monkeypatch.setattr(main.requests, "get", fake_get)
    main.check_ml_client("http://ml:8000")
    assert calls == [("http://ml:8000/health", 3)]


def test_check_ml_client_unknown_without_status(monkeypatch):
    """A reply without a status field is reported as unknown."""
    monkeypatch.setattr(main.requests, "get", lambda url, timeout: FakeResponse({}))
    assert main.check_ml_client("http://ml") == "unknown"


def test_check_ml_client_unreachable_on_connection_error(monkeypatch):
    """A connection failure is reported as unreachable."""

    def fail(url, timeout):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(main.requests, "get", fail)
    assert main.check_ml_client("http://ml") == "unreachable"


def test_check_ml_client_unreachable_on_bad_json(monkeypatch):
    """A reply that is not JSON is reported as unreachable."""
    monkeypatch.setattr(
        main.requests,
        "get",
        lambda url, timeout: FakeResponse(error=ValueError("not json")),
    )
    assert main.check_ml_client("http://ml") == "unreachable"


def test_get_database_uses_given_uri(monkeypatch):
    """The database name comes from the URI path."""
    monkeypatch.setattr(main, "MongoClient", mongomock.MongoClient)
    assert main.get_database("mongodb://localhost/testdb").name == "testdb"


def test_get_database_falls_back_to_env(monkeypatch):
    """Without an argument the URI is read from MONGO_URI."""
    monkeypatch.setattr(main, "MongoClient", mongomock.MongoClient)
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost/envdb")
    assert main.get_database().name == "envdb"


def test_create_app_connects_when_no_database_given(monkeypatch, database):
    """create_app uses get_database when no database is passed."""
    monkeypatch.setattr(main, "get_database", lambda: database)
    assert main.create_app() is not None


def test_create_app_reads_ml_client_url_from_env(monkeypatch, database):
    """The ML client URL comes from ML_CLIENT_URL."""
    urls = []
    monkeypatch.setenv("ML_CLIENT_URL", "http://custom:9000")
    monkeypatch.setattr(main, "check_ml_client", lambda url: urls.append(url) or "ok")

    main.create_app(database).test_client().get("/")

    assert urls == ["http://custom:9000"]
