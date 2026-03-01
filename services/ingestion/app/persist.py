# services/ingestion/app/persist.py
from services.ingestion.db.models import MatchDB as DBMatch
from services.ingestion.db.models import MatchPlayerDB, MatchPlayerItemDB, PlayerDB
from services.ingestion.db.repositories import (
    MatchPlayerItemRepository,
    MatchPlayerRepository,
    MatchRepository,
    PlayerRepository,
)
from services.ingestion.db.unit_of_work import UnitOfWork
from services.ingestion.domains.matches.dtos import Match


def persist_match(match: Match) -> None:
    """Атомарне збереження матчу у БД.

    Зберігає match + players + match_players + match_player_items в одній транзакції.
    item_id=0 (порожній слот) не зберігається — фільтрується тут.
    Всі items з усіх гравців зберігаються одним batch upsert в кінці.
    """
    with UnitOfWork() as uow:
        match_repo = MatchRepository(uow.conn)
        player_repo = PlayerRepository(uow.conn)
        mp_repo = MatchPlayerRepository(uow.conn)
        item_repo = MatchPlayerItemRepository(uow.conn)

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

        all_item_records: list[MatchPlayerItemDB] = []

        for p in match.players:
            player_id = player_repo.upsert(
                PlayerDB(
                    id=None,
                    account_id=p.account_id,
                    rank_tier=None,
                    mmr=None,
                )
            )

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
                    player_slot=p.player_slot,
                )
            )

            all_item_records.extend(
                MatchPlayerItemDB(
                    match_id=match.id,
                    player_slot=p.player_slot,
                    slot=slot_idx,
                    item_id=item_id,
                )
                for slot_idx, item_id in enumerate(p.items)
                if item_id > 0
            )

        if all_item_records:
            item_repo.upsert_batch(all_item_records)