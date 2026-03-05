-- services/analysis/db/schema.sql

CREATE TABLE IF NOT EXISTS watchlist (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id    INTEGER NOT NULL UNIQUE,
    added_at    INTEGER NOT NULL,
    label       TEXT,
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending', 'analyzed', 'error')),
    error       TEXT
);

CREATE TABLE IF NOT EXISTS match_reports (
    match_id        INTEGER PRIMARY KEY,
    draft_data      TEXT,       -- JSON
    economy_data    TEXT,       -- JSON
    teamfight_data  TEXT,       -- JSON
    data_quality    TEXT NOT NULL DEFAULT 'minimal',
    generated_at    INTEGER NOT NULL
);
