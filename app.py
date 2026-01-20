from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from flask import Flask, jsonify, render_template, request


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get("DATABASE", os.path.join(app.instance_path, "app.db"))
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    def get_db() -> sqlite3.Connection:
        conn = sqlite3.connect(app.config["DATABASE"])
        conn.row_factory = sqlite3.Row
        return conn

    def init_db() -> None:
        conn = get_db()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS exam_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    avg_glucose REAL NOT NULL,
                    glucose_sd REAL NOT NULL,
                    difficulty REAL NOT NULL,
                    score REAL NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def now_iso() -> str:
        return datetime.now(timezone.utc).astimezone().isoformat()

    def parse_float(value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def validate_entry(data: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, float]]:
        errors: Dict[str, str] = {}
        parsed: Dict[str, float] = {}

        avg_glucose = parse_float(data.get("avg_glucose"))
        if avg_glucose is None:
            errors["avg_glucose"] = "Average glucose must be a number."
        elif avg_glucose <= 0:
            errors["avg_glucose"] = "Average glucose must be > 0."
        else:
            parsed["avg_glucose"] = avg_glucose

        glucose_sd = parse_float(data.get("glucose_sd"))
        if glucose_sd is None:
            errors["glucose_sd"] = "Glucose SD must be a number."
        elif glucose_sd < 0:
            errors["glucose_sd"] = "Glucose SD must be >= 0."
        else:
            parsed["glucose_sd"] = glucose_sd

        difficulty = parse_float(data.get("difficulty"))
        if difficulty is None:
            errors["difficulty"] = "Difficulty must be a number."
        elif not 1 <= difficulty <= 10:
            errors["difficulty"] = "Difficulty must be between 1 and 10."
        else:
            parsed["difficulty"] = difficulty

        score = parse_float(data.get("score"))
        if score is None:
            errors["score"] = "Score must be a number."
        elif not 0 <= score <= 100:
            errors["score"] = "Score must be between 0 and 100."
        else:
            parsed["score"] = score

        return errors, parsed

    def validate_predict(data: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, float]]:
        errors: Dict[str, str] = {}
        parsed: Dict[str, float] = {}

        avg_glucose = parse_float(data.get("avg_glucose"))
        if avg_glucose is None:
            errors["avg_glucose"] = "Average glucose must be a number."
        elif avg_glucose <= 0:
            errors["avg_glucose"] = "Average glucose must be > 0."
        else:
            parsed["avg_glucose"] = avg_glucose

        glucose_sd = parse_float(data.get("glucose_sd"))
        if glucose_sd is None:
            errors["glucose_sd"] = "Glucose SD must be a number."
        elif glucose_sd < 0:
            errors["glucose_sd"] = "Glucose SD must be >= 0."
        else:
            parsed["glucose_sd"] = glucose_sd

        difficulty = parse_float(data.get("difficulty"))
        if difficulty is None:
            errors["difficulty"] = "Difficulty must be a number."
        elif not 1 <= difficulty <= 10:
            errors["difficulty"] = "Difficulty must be between 1 and 10."
        else:
            parsed["difficulty"] = difficulty

        return errors, parsed

    def fetch_entries() -> List[sqlite3.Row]:
        conn = get_db()
        try:
            cursor = conn.execute(
                "SELECT * FROM exam_entries ORDER BY created_at ASC, id ASC"
            )
            return cursor.fetchall()
        finally:
            conn.close()

    def rows_to_dicts(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
        return [dict(row) for row in rows]

    @app.route("/")
    def index() -> str:
        return render_template("index.html")

    @app.route("/api/entries", methods=["GET"])
    def get_entries() -> Any:
        entries = rows_to_dicts(fetch_entries())
        return jsonify({"entries": entries})

    @app.route("/api/entries", methods=["POST"])
    def add_entry() -> Any:
        data = request.get_json(silent=True) or {}
        errors, parsed = validate_entry(data)
        if errors:
            return jsonify({"errors": errors}), 400

        conn = get_db()
        try:
            created_at = now_iso()
            cursor = conn.execute(
                """
                INSERT INTO exam_entries (created_at, avg_glucose, glucose_sd, difficulty, score)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    parsed["avg_glucose"],
                    parsed["glucose_sd"],
                    parsed["difficulty"],
                    parsed["score"],
                ),
            )
            conn.commit()
            entry_id = cursor.lastrowid
            row = conn.execute(
                "SELECT * FROM exam_entries WHERE id = ?", (entry_id,)
            ).fetchone()
            return jsonify(dict(row)), 201
        finally:
            conn.close()

    @app.route("/api/predict", methods=["POST"])
    def predict() -> Any:
        data = request.get_json(silent=True) or {}
        errors, parsed = validate_predict(data)
        if errors:
            return jsonify({"errors": errors}), 400

        entries = rows_to_dicts(fetch_entries())
        notes: List[str] = []
        model = {
            "type": "multivariate_linear_regression",
            "coefficients": {
                "intercept": 0.0,
                "avg_glucose": 0.0,
                "glucose_sd": 0.0,
                "difficulty": 0.0,
            },
            "n_training_rows": len(entries),
            "r2": None,
        }

        if len(entries) < 3:
            if entries:
                mean_score = float(np.mean([entry["score"] for entry in entries]))
                predicted = mean_score
                notes.append(
                    "Not enough data for regression (need at least 3 rows). "
                    "Returning mean score of existing entries."
                )
            else:
                predicted = 0.0
                notes.append(
                    "No data yet. Returning 0 as a placeholder prediction until entries exist."
                )
            return jsonify(
                {
                    "predicted_score": round(predicted, 2),
                    "model": model,
                    "notes": notes,
                }
            )

        x = np.array(
            [
                [
                    1.0,
                    entry["avg_glucose"],
                    entry["glucose_sd"],
                    entry["difficulty"],
                ]
                for entry in entries
            ]
        )
        y = np.array([entry["score"] for entry in entries])

        coeffs, *_ = np.linalg.lstsq(x, y, rcond=None)
        intercept, b_avg, b_sd, b_diff = coeffs.tolist()

        predicted = (
            intercept
            + b_avg * parsed["avg_glucose"]
            + b_sd * parsed["glucose_sd"]
            + b_diff * parsed["difficulty"]
        )

        y_pred = x.dot(coeffs)
        ss_res = float(np.sum((y - y_pred) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r2 = None
        if ss_tot > 0:
            r2 = 1 - ss_res / ss_tot

        model["coefficients"] = {
            "intercept": float(intercept),
            "avg_glucose": float(b_avg),
            "glucose_sd": float(b_sd),
            "difficulty": float(b_diff),
        }
        model["r2"] = None if r2 is None else round(r2, 4)

        return jsonify(
            {
                "predicted_score": round(float(predicted), 2),
                "model": model,
                "notes": notes,
            }
        )

    init_db()
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
