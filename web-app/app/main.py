"""Dummy web app used to verify container wiring."""

import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, render_template
from pymongo import MongoClient

# app/main.py -> app/ -> web-app/ -> repo root.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def get_database(uri=None):
    """Return the application database from a Mongo URI."""
    client = MongoClient(uri or os.environ["MONGO_URI"], serverSelectionTimeoutMS=5000)
    return client.get_default_database()


def check_ml_client(url):
    """Return the ML client's health status, or "unreachable"."""
    try:
        response = requests.get(f"{url}/health", timeout=3)
        return response.json().get("status", "unknown")
    except (requests.RequestException, ValueError):
        return "unreachable"


def create_app(database=None):
    """Create the Flask app."""
    app = Flask(__name__)
    database = database if database is not None else get_database()
    ml_client_url = os.environ.get("ML_CLIENT_URL", "http://localhost:8000")

    @app.get("/")
    def index():
        docs = list(database.hello.find().sort("created_at", -1).limit(10))
        return render_template(
            "index.html", docs=docs, ml_status=check_ml_client(ml_client_url)
        )

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000)  # nosec B104
