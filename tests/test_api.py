import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app


@pytest.fixture()
def client():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app({"DATABASE": db_path, "TESTING": True})

    with app.test_client() as client:
        yield client

    os.close(db_fd)
    os.unlink(db_path)


def test_entries_roundtrip(client):
    payload = {
        "avg_glucose": 120,
        "glucose_sd": 25,
        "difficulty": 6,
        "score": 88,
    }
    response = client.post(
        "/api/entries", data=json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["avg_glucose"] == payload["avg_glucose"]

    response = client.get("/api/entries")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["entries"]) == 1


def test_predict_fallback(client):
    response = client.post(
        "/api/predict",
        data=json.dumps(
            {"avg_glucose": 110, "glucose_sd": 20, "difficulty": 5}
        ),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["model"]["n_training_rows"] == 0
    assert data["notes"]
