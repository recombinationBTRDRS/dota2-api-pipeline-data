import sqlite3

conn = sqlite3.connect("services/ingestion/db/data.sqlite")
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT match_id,
           COUNT(*) as c,
           SUM(CASE WHEN player_slot < 128 THEN 1 ELSE 0 END) as radiant
    FROM match_players
    GROUP BY match_id
""").fetchall()

for row in rows:
    print(f"match={row['match_id']} total={row['c']} radiant={row['radiant']} dire={row['c'] - row['radiant']}")