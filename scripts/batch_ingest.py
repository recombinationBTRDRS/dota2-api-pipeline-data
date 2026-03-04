#!/usr/bin/env python
# scripts/batch_ingest.py
"""Batch ingest матчів з CSV файлу або списку match_id через аргументи.

Використання:
    # З CSV файлу (один match_id на рядок, або колонка match_id)
    python scripts/batch_ingest.py --csv matches.csv

    # Прямо через аргументи
    python scripts/batch_ingest.py --ids 8709253716 8710000000 8711000000

    # Пропустити вже відомі матчі (за замовчуванням)
    python scripts/batch_ingest.py --csv matches.csv --skip-known

    # Перезаписати вже відомі матчі
    python scripts/batch_ingest.py --csv matches.csv --no-skip-known

    # Dry run — показати що буде інгестовано без реального запиту
    python scripts/batch_ingest.py --csv matches.csv --dry-run

    # Rebuild після інгесту
    python scripts/batch_ingest.py --csv matches.csv --rebuild
"""
import argparse
import csv
import logging
import sys
import time
from pathlib import Path

# Додаємо корінь проекту в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.ingestion.app.ingest_match import ingest_match
from services.ingestion.app.rebuild_all import rebuild_all_computed
from services.ingestion.db.repositories import IngestionLogRepository
from services.ingestion.db.sqlite import init_db
from services.ingestion.db.unit_of_work import UnitOfWork

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_ids_from_csv(path: Path) -> list[int]:
    """Читає match_id з CSV. Підтримує:
    - один match_id на рядок (без заголовка)
    - колонку 'match_id' (з заголовком)
    """
    ids: list[int] = []
    with path.open(newline="") as f:
        sample = f.read(1024)
        f.seek(0)
        has_header = "match_id" in sample.lower()

        if has_header:
            reader = csv.DictReader(f)
            col = next(
                (c for c in (reader.fieldnames or []) if c.lower() == "match_id"),
                None,
            )
            if col is None:
                raise ValueError(f"CSV has no 'match_id' column. Columns: {reader.fieldnames}")
            for row in reader:
                val = row[col].strip()
                if val:
                    ids.append(int(val))
        else:
            reader_plain = csv.reader(f)
            for row in reader_plain:
                if row and row[0].strip():
                    ids.append(int(row[0].strip()))

    return ids


def is_known(match_id: int) -> bool:
    with UnitOfWork() as uow:
        return IngestionLogRepository(uow.conn).is_known(match_id)


def run_batch(
    match_ids: list[int],
    *,
    skip_known: bool = True,
    dry_run: bool = False,
    rebuild: bool = False,
    rate_limit_sec: float = 1.5,
) -> dict:
    """Інгестує список матчів з прогресом і статистикою."""
    total = len(match_ids)
    stats = {"total": total, "ingested": 0, "skipped": 0, "failed": 0, "errors": []}

    logger.info("Batch ingest: %d match_ids | skip_known=%s | dry_run=%s", total, skip_known, dry_run)

    for i, match_id in enumerate(match_ids, 1):
        prefix = f"[{i}/{total}] match_id={match_id}"

        if skip_known and is_known(match_id):
            logger.info("%s — SKIP (already known)", prefix)
            stats["skipped"] += 1
            continue

        if dry_run:
            logger.info("%s — DRY RUN (would ingest)", prefix)
            stats["ingested"] += 1
            continue

        try:
            ingest_match(match_id=match_id)
            logger.info("%s — OK", prefix)
            stats["ingested"] += 1
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            logger.error("%s — FAIL: %s", prefix, error)
            stats["failed"] += 1
            stats["errors"].append((match_id, error))

        # Rate limit між запитами (OpenDota free tier = 60 req/min)
        if i < total:
            time.sleep(rate_limit_sec)

    logger.info(
        "Done: ingested=%d skipped=%d failed=%d",
        stats["ingested"], stats["skipped"], stats["failed"],
    )

    if stats["errors"]:
        logger.warning("Failed match_ids:")
        for mid, err in stats["errors"]:
            logger.warning("  %d: %s", mid, err)

    if rebuild and not dry_run and stats["ingested"] > 0:
        logger.info("Running rebuild...")
        result = rebuild_all_computed()
        logger.info("Rebuild result: %s", result)

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch ingest Dota 2 matches")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--csv", type=Path, help="CSV файл з match_id (один на рядок або колонка match_id)")
    source.add_argument("--ids", nargs="+", type=int, help="Список match_id через пробіл")

    parser.add_argument("--skip-known", dest="skip_known", action="store_true", default=True,
                        help="Пропустити вже відомі матчі (default: True)")
    parser.add_argument("--no-skip-known", dest="skip_known", action="store_false",
                        help="Перезаписати вже відомі матчі")
    parser.add_argument("--dry-run", action="store_true",
                        help="Показати що буде інгестовано без реального запиту")
    parser.add_argument("--rebuild", action="store_true",
                        help="Запустити rebuild pre-computed після інгесту")
    parser.add_argument("--rate-limit", type=float, default=1.5,
                        help="Секунд між запитами (default: 1.5)")

    args = parser.parse_args()

    init_db()

    if args.csv:
        if not args.csv.exists():
            logger.error("CSV file not found: %s", args.csv)
            sys.exit(1)
        match_ids = load_ids_from_csv(args.csv)
        logger.info("Loaded %d match_ids from %s", len(match_ids), args.csv)
    else:
        match_ids = args.ids

    if not match_ids:
        logger.error("No match_ids provided")
        sys.exit(1)

    stats = run_batch(
        match_ids,
        skip_known=args.skip_known,
        dry_run=args.dry_run,
        rebuild=args.rebuild,
        rate_limit_sec=args.rate_limit,
    )

    sys.exit(0 if stats["failed"] == 0 else 1)


if __name__ == "__main__":
    main()