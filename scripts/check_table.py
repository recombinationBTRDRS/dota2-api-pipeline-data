import sqlite3

conn = sqlite3.connect("services/ingestion/db/data.sqlite")
sql = conn.execute(
    "SELECT sql FROM sqlite_master WHERE name='hero_synergy_computed'"
).fetchone()[0]

print(sql)