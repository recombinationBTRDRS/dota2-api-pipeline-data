#services/ingestion/db/sqlite.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.sqlite"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY,
        start_time INTEGER,
        duration INTEGER,
        radiant_win BOOLEAN,
        patch INTEGER,
        region INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER UNIQUE,
        rank_tier INTEGER,
        mmr REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS match_players (
        match_id INTEGER,
        player_id INTEGER,
        hero_id INTEGER,
        kills INTEGER,
        deaths INTEGER,
        assists INTEGER,
        gpm INTEGER,
        xpm INTEGER,
        win BOOLEAN,
        PRIMARY KEY (match_id, player_id)
    )
    """)

    conn.commit()
    conn.close()