"""Machine learning client that scores focus in webcam frames."""

import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from pymongo import MongoClient

from app.analyzer import analyze_image, focus_score

# app/main.py -> app/ -> machine-learning-client/ -> repo root.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def get_database(uri=None):
    """Return the application database from a Mongo URI."""
    client = MongoClient(uri or os.environ["MONGO_URI"], serverSelectionTimeoutMS=5000)
    return client.get_default_database()


def create_app(database=None):
    """Create the Flask app."""
    app = Flask(__name__)
    database = database if database is not None else get_database()

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/analyze")
    def analyze():
        session_id = request.form.get("session_id", "").strip()
        if not session_id:
            return jsonify(error="session_id is required"), 400
        image = request.files.get("image")
        if image is None:
            return jsonify(error="image is required"), 400
        try:
            result = analyze_image(image.read())
        except ValueError as error:
            return jsonify(error=str(error)), 400

        result["focus_score"] = focus_score(
            result["face_detected"], result["eyes_detected"]
        )
        now = datetime.now(timezone.utc)
        # Mongo keeps milliseconds, so drop the rest to match the response.
        now = now.replace(microsecond=now.microsecond // 1000 * 1000)
        database.frames.insert_one({"session_id": session_id, "ts": now, **result})
        return jsonify(ts=now.isoformat(timespec="milliseconds"), **result)

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=8000)  # nosec B104
