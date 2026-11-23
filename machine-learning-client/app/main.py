"""Dummy machine learning client used to verify container wiring."""

import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify
from pymongo import MongoClient

# app/main.py -> app/ -> machine-learning-client/ -> repo root.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def get_database(uri=None):
    """Return the application database from a Mongo URI."""
    client = MongoClient(uri or os.environ["MONGO_URI"], serverSelectionTimeoutMS=5000)
    return client.get_default_database()


def create_app(database=None):
    """Create the Flask app and write a dummy document on startup."""
    app = Flask(__name__)
    database = database if database is not None else get_database()

    database.hello.insert_one(
        {
            "source": "ml-client",
            "message": "Hello from the machine learning client",
            "created_at": datetime.now(timezone.utc),
        }
    )

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=8000)  # nosec B104
