-- services/ingestion/db/schema.sql

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS matches (
    id          INTEGER PRIMARY KEY,
    start_time  INTEGER NOT NULL,
    duration    INTEGER NOT NULL,
    radiant_win BOOLEAN NOT NULL,
    patch       INTEGER,
    region      INTEGER
);

-- account_id може бути NULL для анонімних гравців.
-- SQLite: UNIQUE constraint на nullable column — два різних NULL не конфліктують,
-- тому реальні акаунти дедупліковані, аноніми отримують окремий рядок.
CREATE TABLE IF NOT EXISTS players (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id  INTEGER UNIQUE,
    rank_tier   INTEGER,
    mmr         REAL
);

-- player_slot (0–9) — унікальний слот у матчі (PK разом з match_id).
-- Дозволяє ідемпотентний upsert анонімних гравців по (match_id, player_slot).
-- player_id — FK до players.id (nullable: SET NULL при видаленні гравця).
CREATE TABLE IF NOT EXISTS match_players (
    match_id    INTEGER NOT NULL,
    player_slot INTEGER NOT NULL,
    player_id   INTEGER,
    hero_id     INTEGER NOT NULL,
    kills       INTEGER NOT NULL,
    deaths      INTEGER NOT NULL,
    assists     INTEGER NOT NULL,
    gpm         INTEGER NOT NULL,
    xpm         INTEGER NOT NULL,
    win         BOOLEAN NOT NULL,
    PRIMARY KEY (match_id, player_slot),
    FOREIGN KEY (match_id)  REFERENCES matches(id)  ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(id)  ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_match_players_match_id
    ON match_players (match_id);
CREATE INDEX IF NOT EXISTS idx_match_players_player_id
    ON match_players (player_id);

-- Журнал інжесту матчів (Task 2.3 — Deduplication).
-- match_id — PK, тому кожен матч має рівно один запис.
-- status: 'ok' — успішно збережено, 'failed' — помилка при інжесті.
-- error — текст помилки (truncated до 500 символів), NULL при status='ok'.
-- ingested_at — unix timestamp моменту запису.
CREATE TABLE IF NOT EXISTS ingestion_log (
    match_id    INTEGER PRIMARY KEY,
    status      TEXT    NOT NULL CHECK(status IN ('ok', 'failed')),
    ingested_at INTEGER NOT NULL,
    error       TEXT
);