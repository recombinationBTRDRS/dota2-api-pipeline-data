# services/ingestion/db/repositories.py
import sqlite3

from services.ingestion.db.models import IngestionLogDB, MatchPlayerDB, PlayerDB
from services.ingestion.db.models import MatchDB as DBMatch

_MAX_ERROR_LEN = 500  # максимальна довжина тексту помилки в ingestion_log


class MatchRepository:
    """Репозиторій для таблиці matches."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert(self, match: DBMatch) -> None:
        """Ідемпотентне збереження матчу (INSERT або UPDATE при конфлікті id)."""
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
            (
                match.id,
                match.start_time,
                match.duration,
                match.radiant_win,
                match.patch,
                match.region,
            ),
        )


class PlayerRepository:
    """Репозиторій для таблиці players.

    Обробляє два кейси:
    - account_id IS NULL  → INSERT нового анонімного гравця, повертає lastrowid.
    - account_id NOT NULL → INSERT OR IGNORE + UPDATE, повертає id по account_id.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert(self, player: PlayerDB) -> int:
        """Зберігає гравця і повертає його id у таблиці players."""
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
    """Репозиторій для таблиці match_players.

    PK = (match_id, player_slot) — гарантує ідемпотентність по слоту матчу.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert(self, mp: MatchPlayerDB) -> None:
        """Ідемпотентне збереження участі гравця у матчі."""
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
            (
                mp.match_id,
                mp.player_slot,
                mp.player_id,
                mp.hero_id,
                mp.kills,
                mp.deaths,
                mp.assists,
                mp.gpm,
                mp.xpm,
                mp.win,
            ),
        )


class IngestionLogRepository:
    """Репозиторій для таблиці ingestion_log (Task 2.3 — Deduplication).

    Відповідає за відстеження статусу інжесту кожного матчу.
    Використовується runner-ом щоб не обробляти вже успішно збережені матчі.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def is_known(self, match_id: int) -> bool:
        """Повертає True якщо match_id вже є в журналі зі статусом 'ok'.

        Failed матчі вважаються невідомими — вони мають бути оброблені повторно.

        Args:
            match_id: ідентифікатор матчу.

        Returns:
            True якщо матч вже успішно збережено, False інакше.
        """
        row = self.conn.execute(
            "SELECT 1 FROM ingestion_log WHERE match_id = ? AND status = 'ok'",
            (match_id,),
        ).fetchone()
        return row is not None

    def mark_ok(self, match_id: int, ingested_at: int) -> None:
        """Записує успішний інжест матчу.

        Якщо запис вже є (наприклад був 'failed') — оновлює до 'ok'.

        Args:
            match_id: ідентифікатор матчу.
            ingested_at: unix timestamp завершення інжесту.
        """
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
        """Записує невдалий інжест матчу.

        Якщо запис вже є — оновлює статус і текст помилки.
        Текст помилки truncate до 500 символів.

        Args:
            match_id: ідентифікатор матчу.
            ingested_at: unix timestamp спроби інжесту.
            error: опис помилки.
        """
        truncated = error[:_MAX_ERROR_LEN]
        self.conn.execute(
            """
            INSERT INTO ingestion_log (match_id, status, ingested_at, error)
            VALUES (?, 'failed', ?, ?)
            ON CONFLICT(match_id) DO UPDATE SET
                status      = 'failed',
                ingested_at = excluded.ingested_at,
                error       = excluded.error
            """,
            (match_id, ingested_at, truncated),
        )

    def get(self, match_id: int) -> IngestionLogDB | None:
        """Повертає запис журналу для match_id або None якщо не існує.

        Args:
            match_id: ідентифікатор матчу.

        Returns:
            IngestionLogDB або None.
        """
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