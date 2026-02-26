# services/ingestion/app/__main__.py
"""CLI entrypoint для запуску runner.

Використання:
    python -m services.ingestion.app
    python -m services.ingestion.app --interval 60
"""
import argparse
import logging

from services.ingestion.app.config import settings
from services.ingestion.app.runner import Runner
from services.ingestion.db.sqlite import init_db


def main() -> None:
    """Точка входу: парсить аргументи, ініціалізує БД і запускає runner."""
    parser = argparse.ArgumentParser(description="Dota 2 Match Discovery Runner")
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help=f"Seconds between discovery cycles (default: {settings.DISCOVERY_INTERVAL_SEC})",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    init_db()
    Runner(interval_sec=args.interval).start()


if __name__ == "__main__":
    main()