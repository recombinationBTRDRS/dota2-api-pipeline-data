# services/analysis/app/analyzers/draft.py
from __future__ import annotations

import logging

from services.analysis.app.clients.ingestion import IngestionClient
from services.analysis.domains.reports.dtos import DraftScore

logger = logging.getLogger(__name__)

_MIN_PAIRS_GOOD = 0.50      # > 50% пар знайдено → "good"
_MIN_PAIRS_LIMITED = 0.20   # 20–50% → "limited"; < 20% → "insufficient"


class DraftAnalyzer:
    def __init__(self, client: IngestionClient) -> None:
        self._client = client

    def analyze(
        self,
        radiant_heroes: list[int],
        dire_heroes: list[int],
    ) -> DraftScore:
        """
        Розраховує DraftScore для однієї команди (radiant perspective).
        radiant_heroes / dire_heroes — списки hero_id (5 елементів кожен).
        """
        if not radiant_heroes or not dire_heroes:
            return DraftScore(data_quality="insufficient")

        synergy_score, top_synergies, syn_found, syn_total = self._synergy(radiant_heroes)
        counter_score, top_counters, cnt_found, cnt_total = self._counter(
            radiant_heroes, dire_heroes
        )

        total_pairs = syn_total + cnt_total
        found_pairs = syn_found + cnt_found
        ratio = found_pairs / total_pairs if total_pairs else 0.0

        if ratio >= _MIN_PAIRS_GOOD:
            quality = "good"
        elif ratio >= _MIN_PAIRS_LIMITED:
            quality = "limited"
        else:
            quality = "insufficient"

        overall: float | None = None
        if synergy_score is not None and counter_score is not None:
            overall = round(0.4 * synergy_score + 0.6 * counter_score, 4)
        elif counter_score is not None:
            overall = counter_score
        elif synergy_score is not None:
            overall = synergy_score

        return DraftScore(
            synergy_score=synergy_score,
            counter_score=counter_score,
            overall=overall,
            top_synergies=top_synergies,
            top_counters=top_counters,
            data_quality=quality,
        )

    # ── private ───────────────────────────────────────────────────────────────

    def _synergy(
        self, heroes: list[int]
    ) -> tuple[float | None, list[dict], int, int]:
        """
        Для C(5,2)=10 пар союзників рахуємо середній winrate.
        Повертає (score, top_list, found_count, total_pairs).
        """
        pairs: list[tuple[int, int]] = [
            (heroes[i], heroes[j])
            for i in range(len(heroes))
            for j in range(i + 1, len(heroes))
        ]
        total = len(pairs)
        synergy_data: list[dict] = []

        for hero_a, hero_b in pairs:
            rows = self._client.get_hero_synergies(hero_a, limit=127)
            for row in rows:
                ally_id = row.get("ally_id") or row.get("hero_id_b")
                if ally_id == hero_b and row.get("matches", 0) > 0:
                    winrate = row.get("winrate") or (
                        row["wins"] / row["matches"] if row.get("matches") else None
                    )
                    if winrate is not None:
                        synergy_data.append(
                            {
                                "hero_a_id": hero_a,
                                "hero_b_id": hero_b,
                                "winrate": round(winrate, 4),
                                "matches": row["matches"],
                            }
                        )
                    break

        found = len(synergy_data)
        if not synergy_data:
            return None, [], found, total

        avg = sum(d["winrate"] for d in synergy_data) / found
        top = sorted(synergy_data, key=lambda x: x["winrate"], reverse=True)[:3]
        return round(avg, 4), top, found, total

    def _counter(
        self, my_heroes: list[int], enemy_heroes: list[int]
    ) -> tuple[float | None, list[dict], int, int]:
        """
        Для 5×5=25 пар (мій герой vs ворожий герой) рахуємо середній winrate.
        """
        total = len(my_heroes) * len(enemy_heroes)
        counter_data: list[dict] = []

        for hero in my_heroes:
            rows = self._client.get_hero_matchups(hero, limit=127)
            matchup_map: dict[int, dict] = {}
            for row in rows:
                opp = row.get("opponent_id") or row.get("hero_id_b")
                if opp is not None:
                    matchup_map[opp] = row

            for enemy in enemy_heroes:
                row = matchup_map.get(enemy)
                if row and row.get("matches", 0) > 0:
                    winrate = row.get("winrate") or (
                        row["wins"] / row["matches"] if row.get("matches") else None
                    )
                    if winrate is not None:
                        counter_data.append(
                            {
                                "hero_id": hero,
                                "vs_hero_id": enemy,
                                "winrate": round(winrate, 4),
                                "matches": row["matches"],
                            }
                        )

        found = len(counter_data)
        if not counter_data:
            return None, [], found, total

        avg = sum(d["winrate"] for d in counter_data) / found
        top = sorted(counter_data, key=lambda x: x["winrate"], reverse=True)[:3]
        return round(avg, 4), top, found, total
