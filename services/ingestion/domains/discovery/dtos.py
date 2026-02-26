# services/ingestion/domains/discovery/dtos.py
from pydantic import BaseModel, Field


class DiscoveryFilter(BaseModel):
    """Фільтри для пошуку матчів через OpenDota Explorer API.

    Всі поля мають дефолти з settings — можна перевизначити для конкретного запиту.
    """

    lobby_type: int = Field(default=7, description="7 = ranked matchmaking")
    min_mmr: int = Field(default=3000, ge=0, description="Мінімальний avg_mmr")
    limit: int = Field(default=100, ge=1, le=500, description="Кількість матчів")
    patch: int | None = Field(default=None, description="Номер патчу, None = latest")
    region: int | None = Field(default=None, description="Регіон, None = всі")


class DiscoveredMatch(BaseModel):
    """Результат discovery — один знайдений матч."""

    match_id: int = Field(..., ge=1)