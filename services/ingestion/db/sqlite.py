# services/ingestion/db/sqlite.py
import sqlite3
from pathlib import Path

from services.ingestion.app.config import settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
DB_PATH: Path = Path(settings.DB_PATH)

_MIGRATION_SAFE_ERRORS = (
    "duplicate column name",
    "already exists",
)

_MIGRATIONS = [
    # BL1.1
    "ALTER TABLE matches ADD COLUMN patch INTEGER",
    "ALTER TABLE matches ADD COLUMN region INTEGER",
    # BL1.2
    "ALTER TABLE match_players ADD COLUMN lane_role INTEGER CHECK(lane_role IS NULL OR lane_role BETWEEN 1 AND 4)",
    "ALTER TABLE match_players ADD COLUMN is_roaming BOOLEAN NOT NULL DEFAULT 0",
    "CREATE INDEX IF NOT EXISTS idx_match_players_lane_role ON match_players (lane_role)",
    # Epic 5.1 — hero_stats_computed (AUTOINCREMENT id + COALESCE UNIQUE index)
    """CREATE TABLE IF NOT EXISTS hero_stats_computed (
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
    )""",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_hsc_hero_patch_region_pos ON hero_stats_computed (hero_id, COALESCE(patch, -1), COALESCE(region, -1), primary_pos)",
    "CREATE INDEX IF NOT EXISTS idx_hsc_hero_id     ON hero_stats_computed (hero_id)",
    "CREATE INDEX IF NOT EXISTS idx_hsc_patch       ON hero_stats_computed (patch)",
    "CREATE INDEX IF NOT EXISTS idx_hsc_primary_pos ON hero_stats_computed (primary_pos)",
    # Epic 5.2 — hero_item_build_computed
    """CREATE TABLE IF NOT EXISTS hero_item_build_computed (
        hero_id         INTEGER NOT NULL,
        primary_pos     INTEGER NOT NULL CHECK(primary_pos BETWEEN 1 AND 5),
        item_id         INTEGER NOT NULL,
        times_bought    INTEGER NOT NULL DEFAULT 0,
        times_won       INTEGER NOT NULL DEFAULT 0,
        computed_at     INTEGER NOT NULL,
        PRIMARY KEY (hero_id, primary_pos, item_id),
        FOREIGN KEY (hero_id) REFERENCES heroes(id)  ON DELETE CASCADE,
        FOREIGN KEY (item_id) REFERENCES items(id)   ON DELETE CASCADE
    )""",
    "CREATE INDEX IF NOT EXISTS idx_hibc_hero_pos ON hero_item_build_computed (hero_id, primary_pos)",
]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Виконує міграції ідемпотентно."""
    for sql in _MIGRATIONS:
        try:
            conn.execute(sql)
            conn.commit()
        except sqlite3.OperationalError as e:
            msg = str(e).lower()
            if any(safe in msg for safe in _MIGRATION_SAFE_ERRORS):
                pass
            else:
                raise


def init_db() -> None:
    conn = get_connection()
    try:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        conn.commit()
        _run_migrations(conn)
    finally:
        conn.close()