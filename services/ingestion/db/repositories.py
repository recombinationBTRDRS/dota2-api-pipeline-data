#services/ingestion/db/repositories.py
from .models import Match, MatchPlayer, Player
from .sqlite import get_connection


class MatchRepository:
    def upsert(self, match: Match):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO matches (id, start_time, duration, radiant_win, patch, region)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          start_time=excluded.start_time,
          duration=excluded.duration,
          radiant_win=excluded.radiant_win,
          patch=excluded.patch,
          region=excluded.region
        """, (
            match.id,
            match.start_time,
            match.duration,
            match.radiant_win,
            match.patch,
            match.region
        ))
        conn.commit()
        conn.close()


class PlayerRepository:
    def upsert(self, player: Player) -> int:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO players (account_id, rank_tier, mmr)
        VALUES (?, ?, ?)
        ON CONFLICT(account_id) DO UPDATE SET
          rank_tier=excluded.rank_tier,
          mmr=excluded.mmr
        """, (
            player.account_id,
            player.rank_tier,
            player.mmr
        ))

        conn.commit()
        cur.execute("SELECT id FROM players WHERE account_id = ?", (player.account_id,))
        row = cur.fetchone()
        conn.close()
        return row["id"]


class MatchPlayerRepository:
    def upsert(self, mp: MatchPlayer):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO match_players
        (match_id, player_id, hero_id, kills, deaths, assists, gpm, xpm, win)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(match_id, player_id) DO UPDATE SET
          hero_id=excluded.hero_id,
          kills=excluded.kills,
          deaths=excluded.deaths,
          assists=excluded.assists,
          gpm=excluded.gpm,
          xpm=excluded.xpm,
          win=excluded.win
        """, (
            mp.match_id,
            mp.player_id,
            mp.hero_id,
            mp.kills,
            mp.deaths,
            mp.assists,
            mp.gpm,
            mp.xpm,
            mp.win
        ))
        conn.commit()
        conn.close()