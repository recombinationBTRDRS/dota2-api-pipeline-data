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

CREATE TABLE IF NOT EXISTS players (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id  INTEGER UNIQUE,
    rank_tier   INTEGER,
    mmr         REAL
);

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

CREATE TABLE IF NOT EXISTS ingestion_log (
    match_id    INTEGER PRIMARY KEY,
    status      TEXT    NOT NULL CHECK(status IN ('ok', 'failed')),
    ingested_at INTEGER NOT NULL,
    error       TEXT
);

-- Герої Dota 2 (Task 3.1).
CREATE TABLE IF NOT EXISTS heroes (
    id              INTEGER PRIMARY KEY,
    name            TEXT    NOT NULL UNIQUE,
    localized_name  TEXT    NOT NULL,
    primary_attr    TEXT    NOT NULL CHECK(primary_attr IN ('str', 'agi', 'int', 'all')),
    attack_type     TEXT    NOT NULL CHECK(attack_type IN ('Melee', 'Ranged'))
);

-- Предмети Dota 2 (Task 3.2).
CREATE TABLE IF NOT EXISTS items (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE,
    localized_name TEXT NOT NULL,
    cost        INTEGER NOT NULL DEFAULT 0 CHECK(cost >= 0),
    secret_shop INTEGER NOT NULL DEFAULT 0 CHECK(secret_shop IN (0, 1)),
    side_shop   INTEGER NOT NULL DEFAULT 0 CHECK(side_shop IN (0, 1)),
    recipe      INTEGER NOT NULL DEFAULT 0 CHECK(recipe IN (0, 1))
);

-- Бальна оцінка героїв по позиціях (Task 3.3).
CREATE TABLE IF NOT EXISTS hero_role_scores (
    hero_id     INTEGER PRIMARY KEY,
    pos1        INTEGER NOT NULL CHECK(pos1 BETWEEN 1 AND 5),
    pos2        INTEGER NOT NULL CHECK(pos2 BETWEEN 1 AND 5),
    pos3        INTEGER NOT NULL CHECK(pos3 BETWEEN 1 AND 5),
    pos4        INTEGER NOT NULL CHECK(pos4 BETWEEN 1 AND 5),
    pos5        INTEGER NOT NULL CHECK(pos5 BETWEEN 1 AND 5),
    flex_score  INTEGER NOT NULL CHECK(flex_score BETWEEN 0 AND 5),
    primary_pos INTEGER NOT NULL CHECK(primary_pos BETWEEN 1 AND 5),
    FOREIGN KEY (hero_id) REFERENCES heroes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_hero_role_scores_primary_pos
    ON hero_role_scores (primary_pos);
CREATE INDEX IF NOT EXISTS idx_hero_role_scores_flex
    ON hero_role_scores (flex_score);

-- Предмети гравців у матчі (Task 4.3).
-- slot: 0–5 (6 item slots у Dota 2).
-- item_id > 0 — item_id=0 (порожній слот) не зберігається, фільтрується в persist.py.
-- ON DELETE CASCADE: при видаленні match_players рядка видаляються і його items.
-- Примітка: окремий індекс на (match_id, player_slot) не потрібен —
-- PRIMARY KEY (match_id, player_slot, slot) вже забезпечує B-tree з цим префіксом.
CREATE TABLE IF NOT EXISTS match_player_items (
    match_id    INTEGER NOT NULL,
    player_slot INTEGER NOT NULL,
    slot        INTEGER NOT NULL CHECK(slot BETWEEN 0 AND 5),
    item_id     INTEGER NOT NULL CHECK(item_id > 0),
    PRIMARY KEY (match_id, player_slot, slot),
    FOREIGN KEY (match_id, player_slot)
        REFERENCES match_players(match_id, player_slot) ON DELETE CASCADE
);
