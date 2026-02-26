# services/ingestion/db/unit_of_work.py
import sqlite3
from typing import Literal

from services.ingestion.db.sqlite import get_connection


class UnitOfWork:
    """Контекстний менеджер який гарантує атомарність операцій.

    Всі репозиторії отримують спільне з'єднання через uow.conn.

    Використання:
        with UnitOfWork() as uow:
            MatchRepository(uow.conn).upsert(...)
            PlayerRepository(uow.conn).upsert(...)
    """

    def __enter__(self) -> "UnitOfWork":
        # conn отримує конкретний тип sqlite3.Connection — не Optional.
        # Репозиторії можуть приймати uow.conn без type: ignore.
        self.conn: sqlite3.Connection = get_connection()
        self.conn.execute("BEGIN")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> Literal[False]:
        try:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            self.conn.close()
        return False