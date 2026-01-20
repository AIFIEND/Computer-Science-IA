CREATE TABLE IF NOT EXISTS exam_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    avg_glucose REAL NOT NULL,
    glucose_sd REAL NOT NULL,
    difficulty REAL NOT NULL,
    score REAL NOT NULL
);
