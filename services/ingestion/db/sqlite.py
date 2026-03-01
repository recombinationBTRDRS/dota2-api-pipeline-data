# services/ingestion/db/sqlite.py
import sqlite3
from pathlib import Path

from services.ingestion.app.config import settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

DB_PATH: Path = Path(settings.DB_PATH)

# Безпечні повідомлення OperationalError при ідемпотентних міграціях.
# Будь-яка інша помилка (disk full, locked, permission) — re-raise.
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
    # BL1.2: індекс після того як колонка гарантовано існує
    "CREATE INDEX IF NOT EXISTS idx_match_players_lane_role ON match_players (lane_role)",
]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Виконує міграції ідемпотентно.

    Ігнорує тільки конкретні безпечні помилки (колонка вже існує, індекс вже є).
    Будь-яка інша OperationalError (disk full, locked) — re-raise.
    """
    for sql in _MIGRATIONS:
        try:
            conn.execute(sql)
            conn.commit()
        except sqlite3.OperationalError as e:
            msg = str(e).lower()
            if any(safe in msg for safe in _MIGRATION_SAFE_ERRORS):
                pass  # ідемпотентна ситуація — OK
            else:
                raise


def init_db() -> None:
    """Ініціалізує схему БД (ідемпотентно через IF NOT EXISTS) + міграції."""
    conn = get_connection()
    try:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        conn.commit()
        _run_migrations(conn)
    finally:
        conn.close()