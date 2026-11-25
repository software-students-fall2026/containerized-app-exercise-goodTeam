"""Web app that forwards webcam frames and reports focus results."""

import os
from datetime import timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
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


def forward_frame(url, form, image):
    """Send a frame to the ML client and return its JSON reply and status code."""
    files = None
    if image is not None:
        files = {"image": (image.filename, image.stream, image.mimetype)}
    try:
        response = requests.post(f"{url}/analyze", data=form, files=files, timeout=10)
        if response.status_code >= 500:
            return {"error": "ML client failed"}, 502
        return response.json(), response.status_code
    except (requests.RequestException, ValueError):
        return {"error": "ML client unavailable"}, 502


def summarize(scores):
    """Return the frame count, average score and percentage of scores at 100."""
    count = len(scores)
    if not count:
        return {"count": 0, "avg_focus": 0, "focused_pct": 0}
    return {
        "count": count,
        "avg_focus": round(sum(scores) / count, 1),
        "focused_pct": round(100 * scores.count(100) / count, 1),
    }


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

    @app.post("/frame")
    def frame():
        return forward_frame(
            ml_client_url, request.form.to_dict(), request.files.get("image")
        )

    @app.get("/api/sessions/<session_id>")
    def session(session_id):
        docs = list(database.frames.find({"session_id": session_id}).sort("ts", 1))
        # Mongo returns naive datetimes in UTC.
        frames = [
            {
                "ts": doc["ts"]
                .replace(tzinfo=timezone.utc)
                .isoformat(timespec="milliseconds"),
                "focus_score": doc["focus_score"],
            }
            for doc in docs
        ]
        summary = summarize([doc["focus_score"] for doc in docs])
        return jsonify(frames=frames, summary=summary)

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000)  # nosec B104
