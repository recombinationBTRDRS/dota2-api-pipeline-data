# services/analysis/app/analyzers/economy.py
from __future__ import annotations

import logging

from services.analysis.app.clients.ingestion import IngestionClient
from services.analysis.domains.reports.dtos import EconomySnapshot, PlayerEconomy

logger = logging.getLogger(__name__)

_GPM_THRESHOLD = 0.15   # ±15% від середнього → above/below


class EconomyAnalyzer:
    def __init__(self, client: IngestionClient) -> None:
        self._client = client

    def analyze(self, match_players: list[dict]) -> EconomySnapshot:
        """
        match_players — список dict з полями:
          hero_id, is_radiant, gold_per_min (або gpm), net_worth (опційно),
          kills, deaths, assists
        """
        if not match_players:
            return EconomySnapshot()

        players_economy: list[PlayerEconomy] = []

        for p in match_players:
            hero_id   = p.get("hero_id", 0)
            is_radiant = bool(p.get("is_radiant", True))
            gpm       = int(p.get("gold_per_min") or p.get("gpm") or 0)
            net_worth = p.get("net_worth")

            # Отримати середнє GPM для героя з Ingestion
            stats = self._client.get_hero_stats(hero_id)
            avg_gpm: float | None = None
            if stats:
                mp = stats.get("matches_played") or stats.get("total_matches")
                tg = stats.get("total_gpm") or stats.get("avg_gpm")
                if mp and tg:
                    # якщо avg_gpm вже розраховано в API — беремо напряму
                    avg_gpm = float(tg) if stats.get("avg_gpm") else float(tg) / float(mp)
                elif stats.get("avg_gpm"):
                    avg_gpm = float(stats["avg_gpm"])

            gpm_delta: float | None = None
            gpm_rating = "unknown"
            if avg_gpm and avg_gpm > 0:
                gpm_delta = round(gpm - avg_gpm, 1)
                ratio = gpm_delta / avg_gpm
                if ratio > _GPM_THRESHOLD:
                    gpm_rating = "above_average"
                elif ratio < -_GPM_THRESHOLD:
                    gpm_rating = "below_average"
                else:
                    gpm_rating = "average"

            players_economy.append(PlayerEconomy(
                hero_id=hero_id,
                is_radiant=is_radiant,
                gpm=gpm,
                net_worth=int(net_worth) if net_worth is not None else None,
                avg_gpm_for_hero=round(avg_gpm, 1) if avg_gpm else None,
                gpm_delta=gpm_delta,
                gpm_rating=gpm_rating,
            ))

        radiant = [p for p in players_economy if p.is_radiant]
        dire    = [p for p in players_economy if not p.is_radiant]

        r_nw = sum(p.net_worth for p in radiant if p.net_worth is not None)
        d_nw = sum(p.net_worth for p in dire    if p.net_worth is not None)

        r_gpm = round(sum(p.gpm for p in radiant) / len(radiant), 1) if radiant else 0.0
        d_gpm = round(sum(p.gpm for p in dire)    / len(dire),    1) if dire    else 0.0

        # advantage: порівнюємо net_worth якщо є, інакше GPM
        if r_nw > 0 or d_nw > 0:
            nw_diff = (r_nw - d_nw) / max(r_nw + d_nw, 1)
            if nw_diff > 0.05:
                advantage = "radiant"
            elif nw_diff < -0.05:
                advantage = "dire"
            else:
                advantage = "even"
        else:
            if r_gpm > d_gpm * 1.05:
                advantage = "radiant"
            elif d_gpm > r_gpm * 1.05:
                advantage = "dire"
            else:
                advantage = "even"

        return EconomySnapshot(
            players=players_economy,
            radiant_total_networth=r_nw,
            dire_total_networth=d_nw,
            networth_advantage=advantage,
            radiant_avg_gpm=r_gpm,
            dire_avg_gpm=d_gpm,
        )
