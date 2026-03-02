-- services/ingestion/db/schema.sql

PRAGMA foreign_keys = ON;

-- Raw data

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
    lane_role   INTEGER CHECK(lane_role IS NULL OR lane_role BETWEEN 1 AND 4),
    is_roaming  BOOLEAN NOT NULL DEFAULT 0,
    PRIMARY KEY (match_id, player_slot),
    FOREIGN KEY (match_id)  REFERENCES matches(id)  ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(id)  ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_match_players_match_id ON match_players (match_id);
CREATE INDEX IF NOT EXISTS idx_match_players_hero_id  ON match_players (hero_id);

CREATE TABLE IF NOT EXISTS ingestion_log (
    match_id    INTEGER PRIMARY KEY,
    status      TEXT    NOT NULL CHECK(status IN ('ok', 'failed')),
    ingested_at INTEGER NOT NULL,
    error       TEXT
);

CREATE TABLE IF NOT EXISTS heroes (
    id              INTEGER PRIMARY KEY,
    name            TEXT    NOT NULL UNIQUE,
    localized_name  TEXT    NOT NULL,
    primary_attr    TEXT    NOT NULL CHECK(primary_attr IN ('str', 'agi', 'int', 'all')),
    attack_type     TEXT    NOT NULL CHECK(attack_type IN ('Melee', 'Ranged'))
);

CREATE TABLE IF NOT EXISTS items (
    id             INTEGER PRIMARY KEY,
    name           TEXT    NOT NULL UNIQUE,
    localized_name TEXT    NOT NULL,
    cost           INTEGER NOT NULL DEFAULT 0 CHECK(cost >= 0),
    secret_shop    INTEGER NOT NULL DEFAULT 0 CHECK(secret_shop IN (0, 1)),
    side_shop      INTEGER NOT NULL DEFAULT 0 CHECK(side_shop IN (0, 1)),
    recipe         INTEGER NOT NULL DEFAULT 0 CHECK(recipe IN (0, 1))
);

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

CREATE INDEX IF NOT EXISTS idx_hero_role_scores_primary_pos ON hero_role_scores (primary_pos);
CREATE INDEX IF NOT EXISTS idx_hero_role_scores_flex        ON hero_role_scores (flex_score);

CREATE TABLE IF NOT EXISTS match_player_items (
    match_id    INTEGER NOT NULL,
    player_slot INTEGER NOT NULL,
    slot        INTEGER NOT NULL CHECK(slot BETWEEN 0 AND 5),
    item_id     INTEGER NOT NULL CHECK(item_id > 0),
    PRIMARY KEY (match_id, player_slot, slot),
    FOREIGN KEY (match_id, player_slot)
        REFERENCES match_players(match_id, player_slot) ON DELETE CASCADE
);

-- Pre-computed layer (Epic 5)
-- patch/region = NULL = rollup (aggregate over all patches/regions).
-- PRIMARY KEY excludes patch/region because SQLite treats NULL != NULL,
-- causing duplicates on UPSERT. Uniqueness is enforced via UNIQUE expression
-- index with COALESCE(-1 as sentinel for NULL).

CREATE TABLE IF NOT EXISTS hero_stats_computed (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    hero_id         INTEGER NOT NULL,
    patch           INTEGER,
    region          INTEGER,
    primary_pos     INTEGER NOT NULL CHECK(primary_pos BETWEEN 1 AND 5),
    matches_played  INTEGER NOT NULL DEFAULT 0,
    wins            INTEGER NOT NULL DEFAULT 0,
    total_kills     INTEGER NOT NULL DEFAULT 0,
    total_deaths    INTEGER NOT NULL DEFAULT 0,
    total_assists   INTEGER NOT NULL DEFAULT 0,
    total_gpm       INTEGER NOT NULL DEFAULT 0,
    total_xpm       INTEGER NOT NULL DEFAULT 0,
    computed_at     INTEGER NOT NULL,
    FOREIGN KEY (hero_id) REFERENCES heroes(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_hsc_hero_patch_region_pos
    ON hero_stats_computed (hero_id, COALESCE(patch, -1), COALESCE(region, -1), primary_pos);

CREATE INDEX IF NOT EXISTS idx_hsc_hero_id     ON hero_stats_computed (hero_id);
CREATE INDEX IF NOT EXISTS idx_hsc_patch       ON hero_stats_computed (patch);
CREATE INDEX IF NOT EXISTS idx_hsc_primary_pos ON hero_stats_computed (primary_pos);

CREATE TABLE IF NOT EXISTS hero_item_build_computed (
    hero_id         INTEGER NOT NULL,
    primary_pos     INTEGER NOT NULL CHECK(primary_pos BETWEEN 1 AND 5),
    item_id         INTEGER NOT NULL,
    times_bought    INTEGER NOT NULL DEFAULT 0,
    times_won       INTEGER NOT NULL DEFAULT 0,
    computed_at     INTEGER NOT NULL,
    PRIMARY KEY (hero_id, primary_pos, item_id),
    FOREIGN KEY (hero_id) REFERENCES heroes(id)  ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(id)   ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_hibc_hero_pos ON hero_item_build_computed (hero_id, primary_pos);

-- 5.4 Counter matrix: winrate героя A проти героя B (різні команди)
-- hero_id — герой якого аналізуємо
-- opponent_id — герой суперника
-- wins — кількість перемог hero_id проти opponent_id
CREATE TABLE IF NOT EXISTS hero_matchup_computed (
    hero_id     INTEGER NOT NULL,
    opponent_id INTEGER NOT NULL,
    matches     INTEGER NOT NULL DEFAULT 0,
    wins        INTEGER NOT NULL DEFAULT 0,
    computed_at INTEGER NOT NULL,
    PRIMARY KEY (hero_id, opponent_id),
    FOREIGN KEY (hero_id)     REFERENCES heroes(id) ON DELETE CASCADE,
    FOREIGN KEY (opponent_id) REFERENCES heroes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_hmc_hero_id     ON hero_matchup_computed (hero_id);
CREATE INDEX IF NOT EXISTS idx_hmc_opponent_id ON hero_matchup_computed (opponent_id);

-- 5.5 Synergy matrix: winrate пари (A + B) в одній команді
-- hero_id < ally_id завжди — уникаємо дублів (A,B) і (B,A)
CREATE TABLE IF NOT EXISTS hero_synergy_computed (
    hero_id     INTEGER NOT NULL,
    ally_id     INTEGER NOT NULL,
    matches     INTEGER NOT NULL DEFAULT 0,
    wins        INTEGER NOT NULL DEFAULT 0,
    computed_at INTEGER NOT NULL,
    PRIMARY KEY (hero_id, ally_id),
    CHECK (hero_id < ally_id),
    FOREIGN KEY (hero_id)  REFERENCES heroes(id) ON DELETE CASCADE,
    FOREIGN KEY (ally_id)  REFERENCES heroes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_hsc_synergy_hero ON hero_synergy_computed (hero_id);
CREATE INDEX IF NOT EXISTS idx_hsc_synergy_ally ON hero_synergy_computed (ally_id);