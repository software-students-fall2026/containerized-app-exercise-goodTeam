"""Tests for the ML client app."""

import mongomock

from app import main


def test_health_returns_ok(client):
    """The health endpoint reports ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_create_app_inserts_startup_document(client, database):
    """Creating the app writes one document to the database."""
    assert client is not None
    documents = list(database.hello.find())
    assert len(documents) == 1
    assert documents[0]["source"] == "ml-client"


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
    main.create_app()
    assert database.hello.count_documents({}) == 1
