# services/analysis/app/analyzers/teamfight.py
from __future__ import annotations

import logging

from services.analysis.domains.reports.dtos import TeamfightSnapshot

logger = logging.getLogger(__name__)

_DOMINANT_THRESHOLD = 0.60   # kill_ratio > 0.6 → dominant


class TeamfightAnalyzer:
    def analyze(self, match_players: list[dict]) -> TeamfightSnapshot:
        """
        match_players — список dict з полями:
          is_radiant, kills, deaths, assists
        """
        if not match_players:
            return TeamfightSnapshot()

        radiant = [p for p in match_players if p.get("is_radiant")]
        dire    = [p for p in match_players if not p.get("is_radiant")]

        r_kills = sum(int(p.get("kills") or 0) for p in radiant)
        d_kills = sum(int(p.get("kills") or 0) for p in dire)
        total   = r_kills + d_kills

        kill_ratio = round(r_kills / total, 4) if total > 0 else 0.5

        r_kda = self._avg_kda(radiant)
        d_kda = self._avg_kda(dire)

        if kill_ratio > _DOMINANT_THRESHOLD:
            verdict = "radiant_dominant"
        elif kill_ratio < (1 - _DOMINANT_THRESHOLD):
            verdict = "dire_dominant"
        else:
            verdict = "contested"

        return TeamfightSnapshot(
            radiant_kills=r_kills,
            dire_kills=d_kills,
            kill_ratio=kill_ratio,
            radiant_avg_kda=r_kda,
            dire_avg_kda=d_kda,
            teamfight_verdict=verdict,
        )

    @staticmethod
    def _avg_kda(players: list[dict]) -> float:
        if not players:
            return 0.0
        kdas = []
        for p in players:
            k = int(p.get("kills") or 0)
            d = int(p.get("deaths") or 0)
            a = int(p.get("assists") or 0)
            kda = (k + a) / max(d, 1)
            kdas.append(kda)
        return round(sum(kdas) / len(kdas), 2)
