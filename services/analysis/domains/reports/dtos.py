# services/analysis/domains/reports/dtos.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DraftScore:
    synergy_score: float | None = None
    counter_score: float | None = None
    overall: float | None = None
    top_synergies: list[dict[str, Any]] = field(default_factory=list)
    top_counters: list[dict[str, Any]] = field(default_factory=list)
    data_quality: str = "insufficient"  # "good" | "limited" | "insufficient"


@dataclass
class PlayerEconomy:
    hero_id: int
    is_radiant: bool
    gpm: int
    net_worth: int | None
    avg_gpm_for_hero: float | None
    gpm_delta: float | None
    gpm_rating: str  # "above_average" | "average" | "below_average" | "unknown"


@dataclass
class EconomySnapshot:
    players: list[PlayerEconomy] = field(default_factory=list)
    radiant_total_networth: int = 0
    dire_total_networth: int = 0
    networth_advantage: str = "even"  # "radiant" | "dire" | "even"
    radiant_avg_gpm: float = 0.0
    dire_avg_gpm: float = 0.0


@dataclass
class TeamfightSnapshot:
    radiant_kills: int = 0
    dire_kills: int = 0
    kill_ratio: float = 0.5
    radiant_avg_kda: float = 0.0
    dire_avg_kda: float = 0.0
    teamfight_verdict: str = "contested"  # "radiant_dominant" | "dire_dominant" | "contested"


@dataclass
class MatchReport:
    match_id: int
    generated_at: int
    draft: DraftScore | None = None
    economy: EconomySnapshot | None = None
    teamfight: TeamfightSnapshot | None = None
    data_quality: str = "minimal"  # "complete" | "partial" | "minimal"
