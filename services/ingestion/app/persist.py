# services/ingestion/app/persist.py
from services.ingestion.db.models import MatchDB as DBMatch
from services.ingestion.db.models import MatchPlayerDB, PlayerDB
from services.ingestion.db.repositories import (
    MatchPlayerRepository,
    MatchRepository,
    PlayerRepository,
)
from services.ingestion.db.unit_of_work import UnitOfWork
from services.ingestion.domains.matches.dtos import Match


def persist_match(match: Match) -> None:
    """Атомарне збереження матчу у БД.

    Зберігає match + players + match_players в одній транзакції.
    При будь-якому винятку — автоматичний rollback (через UnitOfWork).

    Args:
        match: провалідований domain Match DTO.
    """
    with UnitOfWork() as uow:
        # uow.conn: sqlite3.Connection — гарантовано після __enter__
        match_repo = MatchRepository(uow.conn)
        player_repo = PlayerRepository(uow.conn)
        mp_repo = MatchPlayerRepository(uow.conn)

        match_repo.upsert(
            DBMatch(
                id=match.id,
                start_time=match.start_time,
                duration=match.duration,
                radiant_win=match.radiant_win,
                patch=None,
                region=None,
            )
        )

        for idx, p in enumerate(match.players):
            player_id = player_repo.upsert(
                PlayerDB(
                    id=None,
                    account_id=p.account_id,
                    rank_tier=None,
                    mmr=None,
                )
            )

            slot = p.player_slot if p.player_slot >= 0 else idx

            mp_repo.upsert(
                MatchPlayerDB(
                    match_id=match.id,
                    player_id=player_id,
                    hero_id=p.hero_id,
                    kills=p.kills,
                    deaths=p.deaths,
                    assists=p.assists,
                    gpm=p.gpm,
                    xpm=p.xpm,
                    win=p.win,
                    player_slot=slot,
                )
            )