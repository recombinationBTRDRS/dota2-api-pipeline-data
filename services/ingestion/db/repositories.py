# services/ingestion/db/repositories.py
import sqlite3

from services.ingestion.db.models import HeroDB, IngestionLogDB, ItemDB, MatchPlayerDB, PlayerDB
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


class ItemRepository:
    """Репозиторій для таблиці items (Task 3.2)."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert_batch(self, items: list[ItemDB]) -> None:
        """Ідемпотентне збереження списку предметів."""
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
            [
                (i.id, i.name, i.localized_name, i.cost,
                 int(i.secret_shop), int(i.side_shop), int(i.recipe))
                for i in items
            ],
        )

    def get(self, item_id: int) -> ItemDB | None:
        """Повертає ItemDB за id або None."""
        row = self.conn.execute(
            "SELECT id, name, localized_name, cost, secret_shop, side_shop, recipe "
            "FROM items WHERE id = ?",
            (item_id,),
        ).fetchone()
        if row is None:
            return None
        return ItemDB(
            id=row["id"],
            name=row["name"],
            localized_name=row["localized_name"],
            cost=row["cost"],
            secret_shop=bool(row["secret_shop"]),
            side_shop=bool(row["side_shop"]),
            recipe=bool(row["recipe"]),
        )

    def get_all(self) -> list[ItemDB]:
        """Повертає всі предмети з таблиці."""
        rows = self.conn.execute(
            "SELECT id, name, localized_name, cost, secret_shop, side_shop, recipe "
            "FROM items ORDER BY id"
        ).fetchall()
        return [
            ItemDB(
                id=r["id"], name=r["name"], localized_name=r["localized_name"],
                cost=r["cost"], secret_shop=bool(r["secret_shop"]),
                side_shop=bool(r["side_shop"]), recipe=bool(r["recipe"]),
            )
            for r in rows
        ]