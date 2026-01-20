# Glucose & Exam Performance Tracker

A lightweight Flask + SQLite app for tracking glucose metrics alongside exam performance and predicting scores from historical data.

## Features
- Add exam entries with glucose metrics, difficulty, and score.
- Persist data in SQLite (auto-creates the database/table on first run).
- View historical entries in a table and a scatter plot.
- Predict scores using multivariate linear regression (refit on demand).

## Tech stack
- **Backend:** Flask
- **Database:** SQLite
- **Frontend:** HTML, CSS, vanilla JS
- **Charts:** Chart.js via CDN
- **Math:** NumPy (least squares regression)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Then visit `http://127.0.0.1:5000`.

## API
- `GET /api/entries` → `{ entries: [...] }`
- `POST /api/entries` → create an entry
- `POST /api/predict` → returns prediction + model metadata

## Notes
- Glucose units are mg/dL.
- Difficulty is 1–10, score is 0–100.
- When fewer than 3 entries exist, predictions fall back to the mean score (or 0 with a note if no data).

## Testing

```bash
pytest
```
