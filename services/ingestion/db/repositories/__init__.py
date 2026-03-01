# services/ingestion/db/repositories/__init__.py
"""Re-export всього публічного API для зворотної сумісності.

Всі існуючі imports вигляду:
    from services.ingestion.db.repositories import MatchRepository
    from services.ingestion.db.repositories import HeroStatsRow
продовжують працювати без змін.
"""
from services.ingestion.db.repositories.analytics import (
    HeroRoleStatsRow,
    HeroStatsRepository,
    HeroStatsRow,
    ItemBuildEntry,
    ItemBuildRepository,
    MatchPhaseStatsRow,
    MatchTimelineRepository,
    MetaHeroRow,
)
from services.ingestion.db.repositories.heroes import (
    HeroRepository,
    HeroRoleScoreRepository,
)
from services.ingestion.db.repositories.items import ItemRepository
from services.ingestion.db.repositories.matches import (
    IngestionLogRepository,
    MatchPlayerItemRepository,
    MatchPlayerRepository,
    MatchRepository,
)
from services.ingestion.db.repositories.players import PlayerRepository

__all__ = [
    # matches
    "MatchRepository",
    "MatchPlayerRepository",
    "MatchPlayerItemRepository",
    "IngestionLogRepository",
    # players
    "PlayerRepository",
    # heroes
    "HeroRepository",
    "HeroRoleScoreRepository",
    # items
    "ItemRepository",
    # analytics
    "HeroStatsRepository",
    "HeroStatsRow",
    "HeroRoleStatsRow",
    "ItemBuildRepository",
    "ItemBuildEntry",
    "MatchTimelineRepository",
    "MatchPhaseStatsRow",
    "MetaHeroRow",
]