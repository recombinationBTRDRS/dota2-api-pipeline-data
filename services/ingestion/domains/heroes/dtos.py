# services/ingestion/domains/heroes/dtos.py
from typing import Literal

from pydantic import BaseModel, Field


class Hero(BaseModel):
    """Domain DTO героя Dota 2.

    Використовується між шарами provider → domain → db.
    primary_attr: 'str' | 'agi' | 'int' | 'all'.
    attack_type: 'Melee' | 'Ranged'.
    """

    id: int = Field(..., ge=1)
    name: str                                            # 'npc_dota_hero_antimage'
    localized_name: str                                  # 'Anti-Mage'
    primary_attr: Literal["str", "agi", "int", "all"]
    attack_type: Literal["Melee", "Ranged"]