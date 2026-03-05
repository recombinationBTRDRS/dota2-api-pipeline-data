# services/analysis/db/repositories/report.py
import json
import sqlite3
from dataclasses import asdict

from services.analysis.domains.reports.dtos import (
    DraftScore,
    EconomySnapshot,
    MatchReport,
    PlayerEconomy,
    TeamfightSnapshot,
)


class ReportRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def save(self, report: MatchReport) -> None:
        self._conn.execute(
            """
            INSERT INTO match_reports
                (match_id, draft_data, economy_data, teamfight_data, data_quality, generated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(match_id) DO UPDATE SET
                draft_data     = excluded.draft_data,
                economy_data   = excluded.economy_data,
                teamfight_data = excluded.teamfight_data,
                data_quality   = excluded.data_quality,
                generated_at   = excluded.generated_at
            """,
            (
                report.match_id,
                json.dumps(asdict(report.draft))      if report.draft      else None,
                json.dumps(asdict(report.economy))    if report.economy    else None,
                json.dumps(asdict(report.teamfight))  if report.teamfight  else None,
                report.data_quality,
                report.generated_at,
            ),
        )

    def get(self, match_id: int) -> MatchReport | None:
        row = self._conn.execute(
            "SELECT match_id, draft_data, economy_data, teamfight_data, "
            "data_quality, generated_at FROM match_reports WHERE match_id = ?",
            (match_id,),
        ).fetchone()
        if not row:
            return None

        draft     = self._load_draft(row["draft_data"])
        economy   = self._load_economy(row["economy_data"])
        teamfight = self._load_teamfight(row["teamfight_data"])

        return MatchReport(
            match_id=row["match_id"],
            generated_at=row["generated_at"],
            draft=draft,
            economy=economy,
            teamfight=teamfight,
            data_quality=row["data_quality"],
        )

    # ── deserializers ─────────────────────────────────────────────────────────

    @staticmethod
    def _load_draft(raw: str | None) -> DraftScore | None:
        if not raw:
            return None
        d = json.loads(raw)
        return DraftScore(**d)

    @staticmethod
    def _load_economy(raw: str | None) -> EconomySnapshot | None:
        if not raw:
            return None
        d = json.loads(raw)
        players = [PlayerEconomy(**p) for p in d.pop("players", [])]
        return EconomySnapshot(players=players, **d)

    @staticmethod
    def _load_teamfight(raw: str | None) -> TeamfightSnapshot | None:
        if not raw:
            return None
        return TeamfightSnapshot(**json.loads(raw))
