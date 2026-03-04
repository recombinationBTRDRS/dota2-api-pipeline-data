# services/ingestion/domains/discovery/dtos.py
from pydantic import BaseModel, Field


class DiscoveryFilter(BaseModel):
    """Фільтри для пошуку матчів через OpenDota Explorer API.

    Обмеження Explorer API (перевірено 2026-03):
    - patch і region колонок більше немає в public_matches
    - Доступні фільтри: lobby_type, avg_rank_tier
    - Максимум 1000 рядків за запит

    Rank Tier шкала:
        10=Herald, 20=Guardian, 30=Crusader, 40=Archon,
        50=Legend, 60=Ancient, 70=Divine, 80+=Immortal
    """

    lobby_type: int = Field(default=7, description="7 = ranked matchmaking")
    min_rank_tier: int = Field(
        default=60,
        ge=0,
        le=89,
        description="Мінімальний avg_rank_tier. 60=Ancient+, 70=Divine+, 80=Immortal+",
    )
    limit: int = Field(default=100, ge=1, le=500, description="Кількість матчів")
    # patch і region залишені для сумісності але ігноруються в SQL
    # (колонки відсутні в public_matches станом на 2026-03)
    patch: int | None = Field(default=None, description="Ігнорується — колонка відсутня в Explorer")
    region: int | None = Field(default=None, description="Ігнорується — колонка відсутня в Explorer")


class DiscoveredMatch(BaseModel):
    """Результат discovery — один знайдений матч."""

    match_id: int = Field(..., ge=1)