# services/ingestion/app/persist.py
from services.ingestion.db.models import MatchDB, MatchPlayerDB, PlayerDB
from services.ingestion.db.repositories import (
    MatchPlayerRepository,
    MatchRepository,
    PlayerRepository,
)
from services.ingestion.db.unit_of_work import UnitOfWork
from services.ingestion.domains.matches.dtos import Match


def persist_match(match: Match) -> None:
    """
    Атомарне збереження матчу.
    match + players + match_players — одна транзакція.
    При будь-якому винятку — повний rollback.
    """
    with UnitOfWork() as uow:
        match_repo = MatchRepository(uow.conn)
        player_repo = PlayerRepository(uow.conn)
        mp_repo = MatchPlayerRepository(uow.conn)

        match_repo.upsert(MatchDB(
            id=match.id,
            start_time=match.start_time,
            duration=match.duration,
            radiant_win=match.radiant_win,
            patch=None,
            region=None,
        ))

        for p in match.players:
            player_id = player_repo.upsert(PlayerDB(
                id=None,
                account_id=p.account_id,
                rank_tier=None,
                mmr=None,
            ))

            mp_repo.upsert(MatchPlayerDB(
                match_id=match.id,
                player_id=player_id,
                hero_id=p.hero_id,
                kills=p.kills,
                deaths=p.deaths,
                assists=p.assists,
                gpm=p.gpm,
                xpm=p.xpm,
                win=p.win,
            ))