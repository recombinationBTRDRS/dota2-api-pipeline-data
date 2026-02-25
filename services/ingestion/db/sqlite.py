# services/ingestion/db/sqlite.py
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data.sqlite"
SCHEMA_PATH = BASE_DIR / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        cur.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()