import sqlite3

conn = sqlite3.connect("services/ingestion/db/data.sqlite")
conn.row_factory = sqlite3.Row

orphans = conn.execute("""
    SELECT DISTINCT a.hero_id, b.hero_id as ally_id
    FROM match_players a
    JOIN match_players b
        ON b.match_id = a.match_id
        AND (a.player_slot < 128) = (b.player_slot < 128)
        AND a.hero_id < b.hero_id
    WHERE a.hero_id NOT IN (SELECT id FROM heroes)
       OR b.hero_id NOT IN (SELECT id FROM heroes)
""").fetchall()

print("Orphan pairs:", len(orphans))
for r in orphans:
    print(r["hero_id"], r["ally_id"])
