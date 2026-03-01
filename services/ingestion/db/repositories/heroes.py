# services/ingestion/db/repositories/heroes.py
"""Репозиторії для героїв і їх рольових оцінок."""
import sqlite3

from services.ingestion.db.models import HeroDB, HeroRoleScoreDB


class HeroRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert(self, hero: HeroDB) -> None:
        self.conn.execute(
            """
            INSERT INTO heroes (id, name, localized_name, primary_attr, attack_type)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name           = excluded.name,
                localized_name = excluded.localized_name,
                primary_attr   = excluded.primary_attr,
                attack_type    = excluded.attack_type
            """,
            (hero.id, hero.name, hero.localized_name, hero.primary_attr, hero.attack_type),
        )

    def upsert_batch(self, heroes: list[HeroDB]) -> None:
        self.conn.executemany(
            """
            INSERT INTO heroes (id, name, localized_name, primary_attr, attack_type)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name           = excluded.name,
                localized_name = excluded.localized_name,
                primary_attr   = excluded.primary_attr,
                attack_type    = excluded.attack_type
            """,
            [(h.id, h.name, h.localized_name, h.primary_attr, h.attack_type) for h in heroes],
        )

    def get(self, hero_id: int) -> HeroDB | None:
        row = self.conn.execute(
            "SELECT id, name, localized_name, primary_attr, attack_type "
            "FROM heroes WHERE id = ?",
            (hero_id,),
        ).fetchone()
        if row is None:
            return None
        return HeroDB(
            id=row["id"], name=row["name"], localized_name=row["localized_name"],
            primary_attr=row["primary_attr"], attack_type=row["attack_type"],
        )

    def get_all(self) -> list[HeroDB]:
        rows = self.conn.execute(
            "SELECT id, name, localized_name, primary_attr, attack_type "
            "FROM heroes ORDER BY id"
        ).fetchall()
        return [
            HeroDB(id=r["id"], name=r["name"], localized_name=r["localized_name"],
                   primary_attr=r["primary_attr"], attack_type=r["attack_type"])
            for r in rows
        ]

    def get_with_role(self, hero_id: int) -> tuple[HeroDB, int | None] | None:
        """Повертає (HeroDB, primary_pos) або None якщо герой не знайдений.

        primary_pos: int 1–5 або None якщо sync_role_scores не запускався.
        Маппінг primary_pos → Role виконується в app/enrich.py — ізоляція шарів.
        """
        row = self.conn.execute(
            """
            SELECT h.id, h.name, h.localized_name, h.primary_attr, h.attack_type,
                   hrs.primary_pos
            FROM heroes h
            LEFT JOIN hero_role_scores hrs ON hrs.hero_id = h.id
            WHERE h.id = ?
            """,
            (hero_id,),
        ).fetchone()
        if row is None:
            return None
        hero = HeroDB(
            id=row["id"], name=row["name"], localized_name=row["localized_name"],
            primary_attr=row["primary_attr"], attack_type=row["attack_type"],
        )
        return hero, row["primary_pos"]


class HeroRoleScoreRepository:
    """Репозиторій для hero_role_scores."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert_batch(self, scores: list[HeroRoleScoreDB]) -> None:
        self.conn.executemany(
            """
            INSERT INTO hero_role_scores
                (hero_id, pos1, pos2, pos3, pos4, pos5, flex_score, primary_pos)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(hero_id) DO UPDATE SET
                pos1        = excluded.pos1,
                pos2        = excluded.pos2,
                pos3        = excluded.pos3,
                pos4        = excluded.pos4,
                pos5        = excluded.pos5,
                flex_score  = excluded.flex_score,
                primary_pos = excluded.primary_pos
            """,
            [(s.hero_id, s.pos1, s.pos2, s.pos3, s.pos4, s.pos5,
              s.flex_score, s.primary_pos) for s in scores],
        )

    def get(self, hero_id: int) -> HeroRoleScoreDB | None:
        row = self.conn.execute(
            "SELECT hero_id, pos1, pos2, pos3, pos4, pos5, flex_score, primary_pos "
            "FROM hero_role_scores WHERE hero_id = ?",
            (hero_id,),
        ).fetchone()
        if row is None:
            return None
        return self._build(row)

    def get_by_pos(self, pos: int, min_score: int = 4) -> list[HeroRoleScoreDB]:
        if pos not in (1, 2, 3, 4, 5):
            raise ValueError(f"pos must be 1-5, got {pos}")
        col = f"pos{pos}"
        rows = self.conn.execute(
            f"SELECT hero_id, pos1, pos2, pos3, pos4, pos5, flex_score, primary_pos "
            f"FROM hero_role_scores WHERE {col} >= ? ORDER BY {col} DESC",
            (min_score,),
        ).fetchall()
        return [self._build(r) for r in rows]

    def get_flex_heroes(self, min_flex: int = 4) -> list[HeroRoleScoreDB]:
        rows = self.conn.execute(
            "SELECT hero_id, pos1, pos2, pos3, pos4, pos5, flex_score, primary_pos "
            "FROM hero_role_scores WHERE flex_score >= ? ORDER BY flex_score DESC",
            (min_flex,),
        ).fetchall()
        return [self._build(r) for r in rows]

    @staticmethod
    def _build(r: sqlite3.Row) -> HeroRoleScoreDB:
        return HeroRoleScoreDB(
            hero_id=r["hero_id"],
            pos1=r["pos1"], pos2=r["pos2"], pos3=r["pos3"],
            pos4=r["pos4"], pos5=r["pos5"],
            flex_score=r["flex_score"], primary_pos=r["primary_pos"],
        )