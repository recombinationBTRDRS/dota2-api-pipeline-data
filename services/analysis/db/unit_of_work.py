# services/analysis/db/unit_of_work.py
import sqlite3
from types import TracebackType
from typing import Self

from services.analysis.db.sqlite import get_connection


class UnitOfWork:
    conn: sqlite3.Connection

    def __enter__(self) -> Self:
        self.conn = get_connection()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.conn.close()
