# services/ingestion/db/sqlite.py
import sqlite3
from pathlib import Path

from services.ingestion.app.config import settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Модуль-рівнева змінна — дозволяє monkeypatch в тестах:
#   monkeypatch.setattr(sqlite_module, "DB_PATH", tmp_path / "test.sqlite")
DB_PATH: Path = Path(settings.DB_PATH)


def get_connection() -> sqlite3.Connection:
    """Відкриває з'єднання до SQLite з row_factory та foreign keys."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Ініціалізує схему БД (ідемпотентно через IF NOT EXISTS)."""
    conn = get_connection()
    try:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()