from services.ingestion.db.models import Match as DBMatch, Player, MatchPlayer
from services.ingestion.db.repositories import MatchRepository, PlayerRepository, MatchPlayerRepository


def persist_match(domain_match):
    match_repo = MatchRepository()
    player_repo = PlayerRepository()
    mp_repo = MatchPlayerRepository()

    match_repo.upsert(DBMatch(
        id=domain_match.id,
        start_time=domain_match.start_time,
        duration=domain_match.duration,
        radiant_win=domain_match.radiant_win,
    ))

    for p in domain_match.players:
        player_id = player_repo.upsert(Player(
            account_id=p.account_id,
            rank_tier=None,
            mmr=None
        ))

        mp_repo.upsert(MatchPlayer(
            match_id=domain_match.id,
            player_id=player_id,
            hero_id=p.hero_id,
            kills=p.kills,
            deaths=p.deaths,
            assists=p.assists,
            gpm=p.gpm,
            xpm=p.xpm,
            win=p.win
        ))