# services/ingestion/db/repositories/items.py
"""Репозиторій для предметів Dota 2."""
import sqlite3

from services.ingestion.db.models import ItemDB


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
        return self._build(row)

    def get_all(self) -> list[ItemDB]:
        rows = self.conn.execute(
            "SELECT id, name, localized_name, cost, secret_shop, side_shop, recipe "
            "FROM items ORDER BY id"
        ).fetchall()
        return [self._build(r) for r in rows]

    @staticmethod
    def _build(r: sqlite3.Row) -> ItemDB:
        return ItemDB(
            id=r["id"], name=r["name"], localized_name=r["localized_name"],
            cost=r["cost"], secret_shop=bool(r["secret_shop"]),
            side_shop=bool(r["side_shop"]), recipe=bool(r["recipe"]),
        )