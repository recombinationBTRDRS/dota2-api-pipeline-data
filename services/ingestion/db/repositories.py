# services/ingestion/db/repositories.py
import sqlite3
from dataclasses import dataclass

from services.ingestion.db.models import (
    HeroDB,
    HeroRoleScoreDB,
    IngestionLogDB,
    ItemDB,
    MatchPlayerDB,
    MatchPlayerItemDB,
    PlayerDB,
)
from services.ingestion.db.models import MatchDB as DBMatch

_MAX_ERROR_LEN = 500


class MatchRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert(self, match: DBMatch) -> None:
        self.conn.execute(
            """
            INSERT INTO matches (id, start_time, duration, radiant_win, patch, region)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                start_time  = excluded.start_time,
                duration    = excluded.duration,
                radiant_win = excluded.radiant_win,
                patch       = excluded.patch,
                region      = excluded.region
            """,
            (match.id, match.start_time, match.duration,
             match.radiant_win, match.patch, match.region),
        )


class PlayerRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert(self, player: PlayerDB) -> int:
        if player.account_id is None:
            cur = self.conn.execute(
                "INSERT INTO players (rank_tier, mmr) VALUES (?, ?)",
                (player.rank_tier, player.mmr),
            )
            lastrowid = cur.lastrowid
            if lastrowid is None:
                raise RuntimeError("INSERT INTO players did not return a lastrowid")
            return int(lastrowid)

        self.conn.execute(
            "INSERT OR IGNORE INTO players (account_id, rank_tier, mmr) VALUES (?, ?, ?)",
            (player.account_id, player.rank_tier, player.mmr),
        )
        self.conn.execute(
            "UPDATE players SET rank_tier = ?, mmr = ? WHERE account_id = ?",
            (player.rank_tier, player.mmr, player.account_id),
        )
        row = self.conn.execute(
            "SELECT id FROM players WHERE account_id = ?",
            (player.account_id,),
        ).fetchone()
        return int(row["id"])


class MatchPlayerRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert(self, mp: MatchPlayerDB) -> None:
        self.conn.execute(
            """
            INSERT INTO match_players
                (match_id, player_slot, player_id, hero_id,
                 kills, deaths, assists, gpm, xpm, win)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(match_id, player_slot) DO UPDATE SET
                player_id = excluded.player_id,
                hero_id   = excluded.hero_id,
                kills     = excluded.kills,
                deaths    = excluded.deaths,
                assists   = excluded.assists,
                gpm       = excluded.gpm,
                xpm       = excluded.xpm,
                win       = excluded.win
            """,
            (mp.match_id, mp.player_slot, mp.player_id, mp.hero_id,
             mp.kills, mp.deaths, mp.assists, mp.gpm, mp.xpm, mp.win),
        )


class IngestionLogRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def is_known(self, match_id: int) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM ingestion_log WHERE match_id = ? AND status = 'ok'",
            (match_id,),
        ).fetchone()
        return row is not None

    def mark_ok(self, match_id: int, ingested_at: int) -> None:
        self.conn.execute(
            """
            INSERT INTO ingestion_log (match_id, status, ingested_at, error)
            VALUES (?, 'ok', ?, NULL)
            ON CONFLICT(match_id) DO UPDATE SET
                status      = 'ok',
                ingested_at = excluded.ingested_at,
                error       = NULL
            """,
            (match_id, ingested_at),
        )

    def mark_failed(self, match_id: int, ingested_at: int, error: str) -> None:
        self.conn.execute(
            """
            INSERT INTO ingestion_log (match_id, status, ingested_at, error)
            VALUES (?, 'failed', ?, ?)
            ON CONFLICT(match_id) DO UPDATE SET
                status      = 'failed',
                ingested_at = excluded.ingested_at,
                error       = excluded.error
            """,
            (match_id, ingested_at, error[:_MAX_ERROR_LEN]),
        )

    def get(self, match_id: int) -> IngestionLogDB | None:
        row = self.conn.execute(
            "SELECT match_id, status, ingested_at, error FROM ingestion_log WHERE match_id = ?",
            (match_id,),
        ).fetchone()
        if row is None:
            return None
        return IngestionLogDB(
            match_id=row["match_id"],
            status=row["status"],
            ingested_at=row["ingested_at"],
            error=row["error"],
        )


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
            "SELECT id, name, localized_name, primary_attr, attack_type FROM heroes WHERE id = ?",
            (hero_id,),
        ).fetchone()
        if row is None:
            return None
        return HeroDB(
            id=row["id"],
            name=row["name"],
            localized_name=row["localized_name"],
            primary_attr=row["primary_attr"],
            attack_type=row["attack_type"],
        )

    def get_all(self) -> list[HeroDB]:
        rows = self.conn.execute(
            "SELECT id, name, localized_name, primary_attr, attack_type FROM heroes ORDER BY id"
        ).fetchall()
        return [
            HeroDB(id=r["id"], name=r["name"], localized_name=r["localized_name"],
                   primary_attr=r["primary_attr"], attack_type=r["attack_type"])
            for r in rows
        ]

    def get_with_role(self, hero_id: int) -> tuple[HeroDB, int | None] | None:
        """Повертає (HeroDB, primary_pos) за hero_id або None якщо герой не знайдений.

        primary_pos: int 1–5 або None якщо sync_role_scores ще не запускався.
        Маппінг primary_pos → Role виконується в app/enrich.py (не в db-шарі).
        db-шар не імпортує з domains/ — ізоляція шарів.
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
            id=row["id"],
            name=row["name"],
            localized_name=row["localized_name"],
            primary_attr=row["primary_attr"],
            attack_type=row["attack_type"],
        )
        return hero, row["primary_pos"]  # primary_pos: int | None


class ItemRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert_batch(self, items: list[ItemDB]) -> None:
        self.conn.executemany(
            """
            INSERT INTO items (id, name, localized_name, cost, secret_shop, side_shop, recipe)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name           = excluded.name,
                localized_name = excluded.localized_name,
                cost           = excluded.cost,
                secret_shop    = excluded.secret_shop,
                side_shop      = excluded.side_shop,
                recipe         = excluded.recipe
            """,
            [(i.id, i.name, i.localized_name, i.cost,
              int(i.secret_shop), int(i.side_shop), int(i.recipe)) for i in items],
        )

    def get(self, item_id: int) -> ItemDB | None:
        row = self.conn.execute(
            "SELECT id, name, localized_name, cost, secret_shop, side_shop, recipe "
            "FROM items WHERE id = ?",
            (item_id,),
        ).fetchone()
        if row is None:
            return None
        return ItemDB(
            id=row["id"], name=row["name"], localized_name=row["localized_name"],
            cost=row["cost"], secret_shop=bool(row["secret_shop"]),
            side_shop=bool(row["side_shop"]), recipe=bool(row["recipe"]),
        )

    def get_all(self) -> list[ItemDB]:
        rows = self.conn.execute(
            "SELECT id, name, localized_name, cost, secret_shop, side_shop, recipe "
            "FROM items ORDER BY id"
        ).fetchall()
        return [
            ItemDB(id=r["id"], name=r["name"], localized_name=r["localized_name"],
                   cost=r["cost"], secret_shop=bool(r["secret_shop"]),
                   side_shop=bool(r["side_shop"]), recipe=bool(r["recipe"]))
            for r in rows
        ]


class HeroRoleScoreRepository:
    """Репозиторій для таблиці hero_role_scores (Task 3.3)."""

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
        return HeroRoleScoreDB(
            hero_id=row["hero_id"],
            pos1=row["pos1"], pos2=row["pos2"], pos3=row["pos3"],
            pos4=row["pos4"], pos5=row["pos5"],
            flex_score=row["flex_score"], primary_pos=row["primary_pos"],
        )

    def get_by_pos(self, pos: int, min_score: int = 4) -> list[HeroRoleScoreDB]:
        if pos not in (1, 2, 3, 4, 5):
            raise ValueError(f"pos must be 1-5, got {pos}")
        col = f"pos{pos}"
        rows = self.conn.execute(
            f"SELECT hero_id, pos1, pos2, pos3, pos4, pos5, flex_score, primary_pos "
            f"FROM hero_role_scores WHERE {col} >= ? ORDER BY {col} DESC",
            (min_score,),
        ).fetchall()
        return [HeroRoleScoreDB(
            hero_id=r["hero_id"],
            pos1=r["pos1"], pos2=r["pos2"], pos3=r["pos3"],
            pos4=r["pos4"], pos5=r["pos5"],
            flex_score=r["flex_score"], primary_pos=r["primary_pos"],
        ) for r in rows]

    def get_flex_heroes(self, min_flex: int = 4) -> list[HeroRoleScoreDB]:
        rows = self.conn.execute(
            "SELECT hero_id, pos1, pos2, pos3, pos4, pos5, flex_score, primary_pos "
            "FROM hero_role_scores WHERE flex_score >= ? ORDER BY flex_score DESC",
            (min_flex,),
        ).fetchall()
        return [HeroRoleScoreDB(
            hero_id=r["hero_id"],
            pos1=r["pos1"], pos2=r["pos2"], pos3=r["pos3"],
            pos4=r["pos4"], pos5=r["pos5"],
            flex_score=r["flex_score"], primary_pos=r["primary_pos"],
        ) for r in rows]


# ── Task 4.1 + 4.2: Hero Stats ────────────────────────────────────────────────

@dataclass(slots=True)
class HeroStatsRow:
    """Raw агрегований рядок з DB (Task 4.1).

    Це db-layer dataclass, не domain DTO.
    Конвертація в domain DTO відбувається в app-шарі якщо потрібно.
    """

    hero_id: int
    hero_name: str | None      # localized_name з JOIN heroes, None якщо немає запису
    matches_played: int
    wins: int
    losses: int
    winrate: float             # wins / matches_played, округлено 4 знаки; 0.0 якщо 0 матчів
    avg_kills: float
    avg_deaths: float
    avg_assists: float
    avg_gpm: float
    avg_xpm: float


@dataclass(slots=True)
class HeroRoleStatsRow:
    """Агрегована статистика героя на конкретній позиції (Task 4.2).

    primary_pos: int 1–5 (db-шар не знає про Role enum).
    Маппінг primary_pos → Role виконується в app-шарі.
    """

    hero_id: int
    hero_name: str | None
    primary_pos: int           # 1=carry, 2=mid, 3=offlane, 4=support, 5=hard_support
    matches_played: int
    wins: int
    losses: int
    winrate: float
    avg_kills: float
    avg_deaths: float
    avg_assists: float
    avg_gpm: float


def _build_hero_stats_row(row: sqlite3.Row) -> HeroStatsRow:
    matches = int(row["matches_played"])
    wins = int(row["wins"])
    return HeroStatsRow(
        hero_id=row["hero_id"],
        hero_name=row["localized_name"],
        matches_played=matches,
        wins=wins,
        losses=matches - wins,
        winrate=round(wins / matches, 4) if matches > 0 else 0.0,
        avg_kills=round(float(row["avg_kills"]), 2),
        avg_deaths=round(float(row["avg_deaths"]), 2),
        avg_assists=round(float(row["avg_assists"]), 2),
        avg_gpm=round(float(row["avg_gpm"]), 2),
        avg_xpm=round(float(row["avg_xpm"]), 2),
    )


def _build_hero_role_stats_row(row: sqlite3.Row) -> HeroRoleStatsRow:
    matches = int(row["matches_played"])
    wins = int(row["wins"])
    return HeroRoleStatsRow(
        hero_id=row["hero_id"],
        hero_name=row["localized_name"],
        primary_pos=int(row["primary_pos"]),
        matches_played=matches,
        wins=wins,
        losses=matches - wins,
        winrate=round(wins / matches, 4) if matches > 0 else 0.0,
        avg_kills=round(float(row["avg_kills"]), 2),
        avg_deaths=round(float(row["avg_deaths"]), 2),
        avg_assists=round(float(row["avg_assists"]), 2),
        avg_gpm=round(float(row["avg_gpm"]), 2),
    )


_HERO_STATS_SQL = """
    SELECT
        mp.hero_id,
        h.localized_name,
        COUNT(*)        AS matches_played,
        SUM(mp.win)     AS wins,
        AVG(mp.kills)   AS avg_kills,
        AVG(mp.deaths)  AS avg_deaths,
        AVG(mp.assists) AS avg_assists,
        AVG(mp.gpm)     AS avg_gpm,
        AVG(mp.xpm)     AS avg_xpm
    FROM match_players mp
    LEFT JOIN heroes h ON h.id = mp.hero_id
"""

# SQL base для role-фільтрованих запитів (Task 4.2).
# JOIN з hero_role_scores дає primary_pos — героїв без запису не включаємо (INNER JOIN).
_HERO_ROLE_STATS_SQL = """
    SELECT
        mp.hero_id,
        h.localized_name,
        hrs.primary_pos,
        COUNT(*)        AS matches_played,
        SUM(mp.win)     AS wins,
        AVG(mp.kills)   AS avg_kills,
        AVG(mp.deaths)  AS avg_deaths,
        AVG(mp.assists) AS avg_assists,
        AVG(mp.gpm)     AS avg_gpm
    FROM match_players mp
    JOIN heroes h ON h.id = mp.hero_id
    JOIN hero_role_scores hrs ON hrs.hero_id = mp.hero_id
"""


class HeroStatsRepository:
    """Аналітичний репозиторій: winrate / pickrate / avg KDA по героях (Task 4.1, 4.2).

    Task 4.1 — загальна статистика по hero_id.
    Task 4.2 — статистика з фільтром по primary_pos (позиції).

    Підхід для Task 4.2: використовуємо hero_role_scores.primary_pos як proxy
    для «герой грав на своїй основній позиції» — без ML, чистий SQL JOIN.
    Герої без запису в hero_role_scores виключаються з role-filtered запитів.

    Всі методи read-only — не змінюють DB.
    Повертає dataclass rows (db-layer), не domain DTOs.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    # ── Task 4.1: загальна статистика ─────────────────────────────────────────

    def get_hero_stats(self, hero_id: int) -> HeroStatsRow | None:
        """Повертає агреговану статистику по одному герою або None якщо немає матчів."""
        row = self.conn.execute(
            _HERO_STATS_SQL + "WHERE mp.hero_id = ? GROUP BY mp.hero_id",
            (hero_id,),
        ).fetchone()
        return _build_hero_stats_row(row) if row is not None else None

    def get_all_heroes_stats(self, min_matches: int = 10) -> list[HeroStatsRow]:
        """Повертає статистику всіх героїв з кількістю матчів >= min_matches."""
        rows = self.conn.execute(
            _HERO_STATS_SQL + """
            GROUP BY mp.hero_id
            HAVING COUNT(*) >= ?
            ORDER BY mp.hero_id
            """,
            (min_matches,),
        ).fetchall()
        return [_build_hero_stats_row(r) for r in rows]

    def get_top_by_winrate(
        self,
        limit: int = 10,
        min_matches: int = 20,
    ) -> list[HeroStatsRow]:
        """Повертає топ героїв за winrate DESC з фільтром min_matches."""
        rows = self.conn.execute(
            _HERO_STATS_SQL + """
            GROUP BY mp.hero_id
            HAVING COUNT(*) >= ?
            ORDER BY (SUM(mp.win) * 1.0 / COUNT(*)) DESC
            LIMIT ?
            """,
            (min_matches, limit),
        ).fetchall()
        return [_build_hero_stats_row(r) for r in rows]

    # ── Task 4.2: статистика по позиції ───────────────────────────────────────

    def get_hero_stats_by_role(
        self,
        hero_id: int,
        primary_pos: int,
    ) -> HeroRoleStatsRow | None:
        """Повертає статистику конкретного героя на конкретній позиції.

        primary_pos: int 1–5 (caller конвертує Role → int якщо потрібно).
        None якщо герой не має запису в hero_role_scores або немає матчів.
        """
        if primary_pos not in (1, 2, 3, 4, 5):
            raise ValueError(f"primary_pos must be 1-5, got {primary_pos}")

        row = self.conn.execute(
            _HERO_ROLE_STATS_SQL + """
            WHERE mp.hero_id = ? AND hrs.primary_pos = ?
            GROUP BY mp.hero_id
            """,
            (hero_id, primary_pos),
        ).fetchone()
        return _build_hero_role_stats_row(row) if row is not None else None

    def get_role_leaderboard(
        self,
        primary_pos: int,
        min_matches: int = 10,
        limit: int = 20,
    ) -> list[HeroRoleStatsRow]:
        """Повертає топ героїв на позиції primary_pos за winrate DESC.

        Включає тільки героїв у яких primary_pos в hero_role_scores = вказаному.
        Тобто «природні» герої цієї позиції, не всі хто там грав.

        primary_pos: int 1–5.
        min_matches: фільтр мінімальної вибірки.
        limit: максимум записів у результаті.
        """
        if primary_pos not in (1, 2, 3, 4, 5):
            raise ValueError(f"primary_pos must be 1-5, got {primary_pos}")

        rows = self.conn.execute(
            _HERO_ROLE_STATS_SQL + """
            WHERE hrs.primary_pos = ?
            GROUP BY mp.hero_id
            HAVING COUNT(*) >= ?
            ORDER BY (SUM(mp.win) * 1.0 / COUNT(*)) DESC
            LIMIT ?
            """,
            (primary_pos, min_matches, limit),
        ).fetchall()
        return [_build_hero_role_stats_row(r) for r in rows]

class MatchPlayerItemRepository:
    """Зберігає предмети гравців у матчі (Task 4.3).

    Тільки write — читання через ItemBuildRepository.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert_batch(self, items: list[MatchPlayerItemDB]) -> None:
        """Ідемпотентне збереження списку item записів.

        ON CONFLICT DO NOTHING — повторний persist_match не дублює записи.
        item_id=0 не передається сюди — фільтрується в persist.py.
        """
        self.conn.executemany(
            """
            INSERT INTO match_player_items (match_id, player_slot, slot, item_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(match_id, player_slot, slot) DO NOTHING
            """,
            [(i.match_id, i.player_slot, i.slot, i.item_id) for i in items],
        )


@dataclass(slots=True)
class ItemBuildEntry:
    """Агрегований запис популярності предмету для героя (Task 4.3).

    Це db-layer dataclass, не domain DTO.
    times_bought: кількість матчів де герой мав цей item.
    pickrate: times_bought / total_matches для цього героя, округлено 4 знаки.
    win_pickrate: times_bought у виграних матчах / total_wins, округлено 4 знаки.
                  0.0 якщо total_wins = 0.
    """

    item_id: int
    item_name: str | None    # localized_name з JOIN items, None якщо items не синкнуті
    times_bought: int
    pickrate: float
    win_pickrate: float


class ItemBuildRepository:
    """Аналітичний репозиторій: популярність предметів по герою (Task 4.3).

    Всі методи read-only.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get_hero_item_build(
        self,
        hero_id: int,
        win_only: bool = False,
        limit: int = 6,
    ) -> list[ItemBuildEntry]:
        """Повертає топ предметів для героя відсортованих за pickrate DESC.

        hero_id: OpenDota hero id.
        win_only: якщо True — рахує тільки матчі де гравець переміг.
        limit: максимум записів (default 6 = повний item build).

        Агрегація: рахує унікальні матчі де герой мав item (не кількість слотів).
        Це коректно бо герой не може мати два однакових item в різних слотах
        у кінці матчу (OpenDota snapshot фінального стану).
        """
        win_filter = "AND mp.win = 1" if win_only else ""

        # Підзапит: total_matches (або total_wins) для нормалізації pickrate
        total_sql = f"""
            SELECT COUNT(DISTINCT mp.match_id)
            FROM match_players mp
            WHERE mp.hero_id = ? {win_filter}
        """
        total_row = self.conn.execute(total_sql, (hero_id,)).fetchone()
        total = int(total_row[0]) if total_row else 0

        if total == 0:
            return []

        rows = self.conn.execute(
            f"""
            SELECT
                mpi.item_id,
                i.localized_name,
                COUNT(DISTINCT mpi.match_id) AS times_bought
            FROM match_player_items mpi
            JOIN match_players mp
                ON mp.match_id = mpi.match_id
               AND mp.player_slot = mpi.player_slot
            LEFT JOIN items i ON i.id = mpi.item_id
            WHERE mp.hero_id = ? {win_filter}
            GROUP BY mpi.item_id
            ORDER BY times_bought DESC
            LIMIT ?
            """,
            (hero_id, limit),
        ).fetchall()

        # win_pickrate завжди відносно wins, незалежно від win_only
        total_wins_row = self.conn.execute(
            "SELECT COUNT(DISTINCT match_id) FROM match_players WHERE hero_id = ? AND win = 1",
            (hero_id,),
        ).fetchone()
        total_wins = int(total_wins_row[0]) if total_wins_row else 0

        result = []
        for row in rows:
            times = int(row["times_bought"])

            # win_pickrate: скільки разів item зустрічається у виграних матчах
            win_row = self.conn.execute(
                """
                SELECT COUNT(DISTINCT mpi.match_id)
                FROM match_player_items mpi
                JOIN match_players mp
                    ON mp.match_id = mpi.match_id
                   AND mp.player_slot = mpi.player_slot
                WHERE mp.hero_id = ? AND mpi.item_id = ? AND mp.win = 1
                """,
                (hero_id, row["item_id"]),
            ).fetchone()
            win_times = int(win_row[0]) if win_row else 0

            result.append(ItemBuildEntry(
                item_id=row["item_id"],
                item_name=row["localized_name"],
                times_bought=times,
                pickrate=round(times / total, 4),
                win_pickrate=round(win_times / total_wins, 4) if total_wins > 0 else 0.0,
            ))

        return result


# Match phase thresholds (seconds)
_EARLY_MAX = 1800   # ≤ 30 хвилин
_MID_MAX = 3000     # 30–50 хвилин
# late = > 50 хвилин


def _duration_to_phase(duration: int) -> str:
    if duration <= _EARLY_MAX:
        return "early"
    if duration <= _MID_MAX:
        return "mid"
    return "late"


@dataclass(slots=True)
class MatchPhaseStatsRow:
    """Статистика героя в конкретній фазі гри (Task 4.4a).

    phase: 'early' | 'mid' | 'late' — визначається через matches.duration.
    Це db-layer dataclass, не domain DTO.
    """

    hero_id: int
    phase: str              # 'early' | 'mid' | 'late'
    matches_played: int
    wins: int
    winrate: float          # округлено 4 знаки
    avg_gpm: float
    avg_kills: float


@dataclass(slots=True)
class MetaHeroRow:
    """Рядок meta snapshot — герой + позиція + агрегована meta_score (Task 4.4b).

    primary_pos: int 1–5 (db-шар не знає про Role enum).
    meta_score: winrate * pickrate * 100, округлено 2 знаки.
    pickrate: matches_played / total_matches_in_sample, округлено 4 знаки.
    """

    hero_id: int
    hero_name: str | None
    primary_pos: int
    matches_played: int
    wins: int
    winrate: float
    pickrate: float
    meta_score: float


class MatchTimelineRepository:
    """Аналітика матчів по фазах гри і meta snapshot (Task 4.4).

    4.4a — get_hero_phase_stats: winrate/gpm по early/mid/late для героя.
    4.4b — get_meta_snapshot: топ героїв по позиціях за meta_score.

    match phase визначається через matches.duration:
        early  ≤ 1800s (≤ 30 хв)
        mid    1801–3000s (30–50 хв)
        late   > 3000s (> 50 хв)

    Всі методи read-only.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get_hero_phase_stats(self, hero_id: int) -> list[MatchPhaseStatsRow]:
        """Повертає статистику героя по фазах гри (до 3 записів).

        Фази без матчів не повертаються.
        Порядок: early → mid → late.
        """
        rows = self.conn.execute(
            """
            SELECT
                mp.hero_id,
                CASE
                    WHEN m.duration <= 1800 THEN 'early'
                    WHEN m.duration <= 3000 THEN 'mid'
                    ELSE 'late'
                END AS phase,
                COUNT(*)        AS matches_played,
                SUM(mp.win)     AS wins,
                AVG(mp.gpm)     AS avg_gpm,
                AVG(mp.kills)   AS avg_kills
            FROM match_players mp
            JOIN matches m ON m.id = mp.match_id
            WHERE mp.hero_id = ?
            GROUP BY phase
            ORDER BY
                CASE phase
                    WHEN 'early' THEN 1
                    WHEN 'mid'   THEN 2
                    ELSE              3
                END
            """,
            (hero_id,),
        ).fetchall()

        result = []
        for row in rows:
            matches = int(row["matches_played"])
            wins = int(row["wins"])
            result.append(MatchPhaseStatsRow(
                hero_id=hero_id,
                phase=row["phase"],
                matches_played=matches,
                wins=wins,
                winrate=round(wins / matches, 4) if matches > 0 else 0.0,
                avg_gpm=round(float(row["avg_gpm"]), 2),
                avg_kills=round(float(row["avg_kills"]), 2),
            ))
        return result

    def get_meta_snapshot(
        self,
        primary_pos: int | None = None,
        limit: int = 10,
    ) -> list[MetaHeroRow]:
        """Повертає топ героїв за meta_score DESC.

        meta_score = winrate * pickrate * 100, округлено 2 знаки.
        pickrate = matches_played / total_matches_in_sample.

        primary_pos: якщо None — всі позиції; інакше фільтр по конкретній позиції.
        Герої без hero_role_scores запису виключаються (INNER JOIN).

        Порожній список якщо нема матчів.
        """
        if primary_pos is not None and primary_pos not in (1, 2, 3, 4, 5):
            raise ValueError(f"primary_pos must be 1-5 or None, got {primary_pos}")

        # total_matches — загальна кількість матчів у вибірці для pickrate
        total_row = self.conn.execute(
            "SELECT COUNT(DISTINCT match_id) FROM match_players"
        ).fetchone()
        total = int(total_row[0]) if total_row else 0

        if total == 0:
            return []

        pos_filter = "AND hrs.primary_pos = ?" if primary_pos is not None else ""
        params: tuple[int, ...] = (primary_pos, limit) if primary_pos is not None else (limit,)

        rows = self.conn.execute(
            f"""
            SELECT
                mp.hero_id,
                h.localized_name,
                hrs.primary_pos,
                COUNT(*)        AS matches_played,
                SUM(mp.win)     AS wins
            FROM match_players mp
            JOIN heroes h ON h.id = mp.hero_id
            JOIN hero_role_scores hrs ON hrs.hero_id = mp.hero_id
            WHERE 1=1 {pos_filter}
            GROUP BY mp.hero_id
            ORDER BY
                (SUM(mp.win) * 1.0 / COUNT(*))
                * (COUNT(*) * 1.0 / {total})
                * 100 DESC
            LIMIT ?
            """,
            params,
        ).fetchall()

        result = []
        for row in rows:
            matches = int(row["matches_played"])
            wins = int(row["wins"])
            winrate = round(wins / matches, 4) if matches > 0 else 0.0
            pickrate = round(matches / total, 4)
            meta_score = round(winrate * pickrate * 100, 2)
            result.append(MetaHeroRow(
                hero_id=row["hero_id"],
                hero_name=row["localized_name"],
                primary_pos=int(row["primary_pos"]),
                matches_played=matches,
                wins=wins,
                winrate=winrate,
                pickrate=pickrate,
                meta_score=meta_score,
            ))
        return result
