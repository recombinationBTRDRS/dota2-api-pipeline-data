# services/ingestion/db/models.py
from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True)
class MatchDB:
    """DB-представлення матчу (окремо від domain DTO)."""

    id: int
    start_time: int
    duration: int
    radiant_win: bool
    patch: int | None
    region: int | None


@dataclass(slots=True)
class PlayerDB:
    """DB-представлення гравця. account_id може бути None для анонімів."""

    id: int | None
    account_id: int | None
    rank_tier: int | None
    mmr: float | None


@dataclass(slots=True)
class MatchPlayerDB:
    """DB-представлення участі гравця у матчі.

    player_slot (0–9) — унікальний слот у матчі, частина PK (match_id, player_slot).
    Обов'язкове поле — caller відповідає за передачу коректного значення.
    player_id — FK до players.id.
    """

    match_id: int
    player_id: int | None
    hero_id: int
    kills: int
    deaths: int
    assists: int
    gpm: int
    xpm: int
    win: bool
    player_slot: int


@dataclass(slots=True)
class IngestionLogDB:
    """DB-представлення запису в журналі інжесту.

    status: 'ok' — успішно збережено, 'failed' — помилка при інжесті.
    error: текст помилки (max 500 символів), None при status='ok'.
    ingested_at: unix timestamp.
    """

    match_id: int
    status: Literal["ok", "failed"]
    ingested_at: int
    error: str | None