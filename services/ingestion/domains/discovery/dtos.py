# services/ingestion/domains/discovery/dtos.py
from pydantic import BaseModel, Field


class DiscoveryFilter(BaseModel):
    """Фільтри для пошуку матчів через OpenDota Explorer API.

    Epic 7.1: min_mmr замінено на min_rank_tier.
    OpenDota видалила avg_mmr з public_matches.
    Шкала avg_rank_tier: 10=Herald, 20=Guardian, 30=Crusader,
    40=Archon, 50=Legend, 60=Ancient, 70=Divine, 80+=Immortal.
    """

    lobby_type: int = Field(default=7, description="7 = ranked matchmaking")
    min_rank_tier: int = Field(
        default=60,
        ge=0,
        le=89,
        description="Мінімальний avg_rank_tier. 60=Ancient+, 70=Divine+, 80=Immortal+",
    )
    limit: int = Field(default=100, ge=1, le=500, description="Кількість матчів")
    patch: int | None = Field(default=None, description="Номер патчу, None = latest")
    region: int | None = Field(default=None, description="Регіон, None = всі")


class DiscoveredMatch(BaseModel):
    """Результат discovery — один знайдений матч."""

    match_id: int = Field(..., ge=1)