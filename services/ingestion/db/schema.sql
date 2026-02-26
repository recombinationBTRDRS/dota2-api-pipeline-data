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
-- id = OpenDota hero id (не AUTOINCREMENT — використовуємо id з API).
-- primary_attr: 'str' | 'agi' | 'int' | 'all' (universal heroes).
-- attack_type: 'Melee' | 'Ranged'.
CREATE TABLE IF NOT EXISTS heroes (
    id              INTEGER PRIMARY KEY,
    name            TEXT    NOT NULL UNIQUE,  -- internal name: 'npc_dota_hero_antimage'
    localized_name  TEXT    NOT NULL,          -- display name: 'Anti-Mage'
    primary_attr    TEXT    NOT NULL CHECK(primary_attr IN ('str', 'agi', 'int', 'all')),
    attack_type     TEXT    NOT NULL CHECK(attack_type IN ('Melee', 'Ranged'))
);