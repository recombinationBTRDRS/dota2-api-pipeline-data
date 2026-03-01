# services/ingestion/db/sqlite.py
import sqlite3
from pathlib import Path

from services.ingestion.app.config import settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

DB_PATH: Path = Path(settings.DB_PATH)

# Міграції для існуючих DB — виконуються після init_db якщо колонки ще немає.
# Додаємо сюди при кожній зміні схеми що додає нові колонки.
# IF NOT EXISTS не працює для ALTER TABLE — тому перевіряємо через pragma.
_MIGRATIONS = [
    # BL1.1
    "ALTER TABLE matches ADD COLUMN patch INTEGER",
    "ALTER TABLE matches ADD COLUMN region INTEGER",
    # BL1.2
    "ALTER TABLE match_players ADD COLUMN lane_role INTEGER CHECK(lane_role IS NULL OR lane_role BETWEEN 1 AND 4)",
    "ALTER TABLE match_players ADD COLUMN is_roaming BOOLEAN NOT NULL DEFAULT 0",
    # BL1.2: індекс по lane_role — після того як колонка гарантовано існує
    "CREATE INDEX IF NOT EXISTS idx_match_players_lane_role ON match_players (lane_role)",
]


def get_connection() -> sqlite3.Connection:
    """Відкриває з'єднання до SQLite з row_factory та foreign keys."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Виконує міграції ідемпотентно — ігнорує помилку якщо колонка вже є."""
    for sql in _MIGRATIONS:
        try:
            conn.execute(sql)
            conn.commit()
        except sqlite3.OperationalError:
            # Колонка або індекс вже існує — нормальна ситуація
            pass


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