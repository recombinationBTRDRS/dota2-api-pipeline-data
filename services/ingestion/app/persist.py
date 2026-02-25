# services/ingestion/app/persist.py
from services.ingestion.db.sqlite import get_connection
from services.ingestion.db.repositories import (
    MatchRepository,
    PlayerRepository,
    MatchPlayerRepository,
)
from services.ingestion.db.models import MatchDB, PlayerDB, MatchPlayerDB
from services.ingestion.domains.matches.dtos import Match


def persist_match(match: Match) -> None:
    """
    Єдина точка перетворення domain → db + атомарне збереження
    """
    conn = get_connection()
    try:
        conn.execute("BEGIN")

        match_repo = MatchRepository()
        player_repo = PlayerRepository()
        mp_repo = MatchPlayerRepository()

        match_db = MatchDB(
            id=match.id,
            start_time=match.start_time,
            duration=match.duration,
            radiant_win=match.radiant_win,
            patch=None,
            region=None,
        )

        match_repo.upsert(match_db)

        for p in match.players:
            player_db = PlayerDB(
                id=None,
                account_id=p.account_id,
                rank_tier=None,
                mmr=None,
            )
            player_id = player_repo.upsert(player_db)

            mp_db = MatchPlayerDB(
                match_id=match.id,
                player_id=player_id,
                hero_id=p.hero_id,
                kills=p.kills,
                deaths=p.deaths,
                assists=p.assists,
                gpm=p.gpm,
                xpm=p.xpm,
                win=p.win,
            )
            mp_repo.upsert(mp_db)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()