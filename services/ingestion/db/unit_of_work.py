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
            # commit автоматично при виході
            # rollback автоматично при винятку
    """

    def __init__(self) -> None:
        self.conn: sqlite3.Connection | None = None

    def __enter__(self) -> "UnitOfWork":
        self.conn = get_connection()
        self.conn.execute("BEGIN")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> Literal[False]:
        # mypy вимагає Literal[False] якщо __exit__ ніколи не повертає True
        assert self.conn is not None  # гарантовано після __enter__
        try:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            self.conn.close()
            self.conn = None
        return False