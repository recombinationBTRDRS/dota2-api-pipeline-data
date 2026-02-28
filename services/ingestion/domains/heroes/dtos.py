# services/ingestion/domains/heroes/dtos.py
from typing import Literal

from pydantic import BaseModel, Field

from services.ingestion.domains.roles.dtos import Role


class Hero(BaseModel):
    """Domain DTO героя Dota 2.

    Використовується між шарами provider → domain → db.

    Notes:
        primary_attr: 'str' | 'agi' | 'int' | 'all'
            Значення 'all' використовується як дефолт для фейкових провайдерів у тестах.
        attack_type: 'Melee' | 'Ranged'
    """

    id: int = Field(..., ge=1)
    name: str                                            # 'npc_dota_hero_antimage'
    localized_name: str                                  # 'Anti-Mage'
    primary_attr: Literal["str", "agi", "int", "all"]
    attack_type: Literal["Melee", "Ranged"]


class EnrichedPlayerStats(BaseModel):
    """Статистика гравця збагачена даними героя і ролі (Task 3.4).

    Read-only модель — створюється в enrich_match(), не зберігається в DB.

    hero і role можуть бути None якщо герой не знайдений в DB
    (graceful degradation — герой міг не пройти sync_heroes).

    player_slot: 0–9, унікальний в межах матчу.
    """

    model_config = {"frozen": True}

    # ── ідентифікація ──────────────────────────────────────────────────────────
    match_id: int
    player_slot: int

    # ── статистика гравця (з Match.players) ───────────────────────────────────
    account_id: int | None
    hero_id: int
    kills: int
    deaths: int
    assists: int
    gpm: int
    xpm: int
    is_radiant: bool
    win: bool

    # ── збагачення з DB ────────────────────────────────────────────────────────
    hero_name: str | None          # localized_name, None якщо не знайдено в DB
    primary_attr: str | None       # 'str' | 'agi' | 'int' | 'all'
    attack_type: str | None        # 'Melee' | 'Ranged'
    role: Role | None              # primary_pos → Role enum, None якщо не знайдено