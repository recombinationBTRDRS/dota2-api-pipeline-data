#!/usr/bin/env python
# scripts/discover_and_ingest.py
"""Розширений discovery + ingest з гнучкими фільтрами.

Дозволяє знаходити матчі за конкретними параметрами (MMR, регіон, патч, дата)
і одразу інгестувати їх. Корисний для збору даних за конкретний період або мету.

Використання:
    # Знайти і інгестувати 200 матчів Divine+ з EU West
    python scripts/discover_and_ingest.py --count 200 --rank-tier 70 --region 3

    # Матчі за конкретний патч, dry-run спочатку
    python scripts/discover_and_ingest.py --count 100 --patch 59 --dry-run

    # Тільки discovery — зберегти match_id в CSV без інгесту
    python scripts/discover_and_ingest.py --count 500 --save-csv found_matches.csv --no-ingest

    # Повний pipeline: знайти → інгестувати → rebuild
    python scripts/discover_and_ingest.py --count 100 --rank-tier 60 --rebuild

Регіони OpenDota:
    1=US West, 2=US East, 3=Europe, 4=SE Asia, 5=China, 6=Dubai, 7=Australia,
    8=Stockholm, 9=Vienna, 10=Peru, 11=India, 12=South Africa, 13=China (Telecom)

Rank Tier:
    10=Herald, 20=Guardian, 30=Crusader, 40=Archon,
    50=Legend, 60=Ancient, 70=Divine, 80=Immortal
"""
import argparse
import csv
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.ingestion.app.ingest_match import ingest_match
from services.ingestion.app.rebuild_all import rebuild_all_computed
from services.ingestion.db.repositories import IngestionLogRepository
from services.ingestion.db.sqlite import init_db
from services.ingestion.db.unit_of_work import UnitOfWork
from services.ingestion.domains.discovery.dtos import DiscoveryFilter
from services.ingestion.providers.opendota.explorer_client import OpenDotaExplorerClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

REGION_NAMES = {
    1: "US West", 2: "US East", 3: "Europe", 4: "SE Asia",
    5: "China", 6: "Dubai", 7: "Australia", 8: "Stockholm",
    9: "Vienna", 10: "Peru", 11: "India", 12: "South Africa",
}

RANK_NAMES = {
    10: "Herald", 20: "Guardian", 30: "Crusader", 40: "Archon",
    50: "Legend", 60: "Ancient", 70: "Divine", 80: "Immortal",
}


def get_rank_label(tier: int) -> str:
    base = (tier // 10) * 10
    return RANK_NAMES.get(base, f"Tier {tier}")


def is_known(match_id: int) -> bool:
    with UnitOfWork() as uow:
        return IngestionLogRepository(uow.conn).is_known(match_id)


def discover_matches(
    count: int,
    rank_tier: int,
    region: int | None,
    patch: int | None,
    lobby_type: int,
) -> list[int]:
    """Discovery через OpenDota Explorer. Повертає список match_id."""
    # Explorer повертає max 1000 рядків за раз — робимо кілька запитів якщо треба
    all_ids: list[int] = []
    batch_size = min(count, 500)  # Explorer ліміт

    client = OpenDotaExplorerClient()
    f = DiscoveryFilter(
        lobby_type=lobby_type,
        min_rank_tier=rank_tier,
        limit=batch_size,
        patch=patch,
        region=region,
    )

    logger.info(
        "Discovering: count=%d rank=%s region=%s patch=%s",
        count,
        get_rank_label(rank_tier),
        REGION_NAMES.get(region, region) if region else "All",
        patch or "latest",
    )

    discovered = client.discover(f)
    all_ids = [m.match_id for m in discovered]

    logger.info("Discovered %d match_ids", len(all_ids))
    return all_ids[:count]


def save_to_csv(match_ids: list[int], path: Path) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["match_id"])
        for mid in match_ids:
            writer.writerow([mid])
    logger.info("Saved %d match_ids to %s", len(match_ids), path)


def run_ingest(
    match_ids: list[int],
    *,
    skip_known: bool = True,
    dry_run: bool = False,
    rate_limit_sec: float = 1.5,
) -> dict:
    total = len(match_ids)
    stats = {"total": total, "ingested": 0, "skipped": 0, "failed": 0, "errors": []}

    for i, match_id in enumerate(match_ids, 1):
        prefix = f"[{i}/{total}] match_id={match_id}"

        if skip_known and is_known(match_id):
            logger.info("%s — SKIP", prefix)
            stats["skipped"] += 1
            continue

        if dry_run:
            logger.info("%s — DRY RUN", prefix)
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

        if i < total:
            time.sleep(rate_limit_sec)

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover and ingest Dota 2 matches with filters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Discovery параметри
    parser.add_argument("--count", type=int, default=100,
                        help="Кількість матчів для знаходження (default: 100)")
    parser.add_argument("--rank-tier", type=int, default=60,
                        help="Мінімальний rank tier: 60=Ancient+, 70=Divine+, 80=Immortal+ (default: 60)")
    parser.add_argument("--region", type=int, default=None,
                        help="Регіон: 3=Europe, 4=SE Asia і т.д. (default: всі)")
    parser.add_argument("--patch", type=int, default=None,
                        help="Номер патчу (default: останній)")
    parser.add_argument("--lobby-type", type=int, default=7,
                        help="Тип лобі: 7=ranked (default: 7)")

    # Поведінка
    parser.add_argument("--skip-known", dest="skip_known", action="store_true", default=True)
    parser.add_argument("--no-skip-known", dest="skip_known", action="store_false")
    parser.add_argument("--dry-run", action="store_true",
                        help="Показати що буде зроблено без реальних запитів")
    parser.add_argument("--no-ingest", action="store_true",
                        help="Тільки discovery — не інгестувати")
    parser.add_argument("--rebuild", action="store_true",
                        help="Rebuild pre-computed після інгесту")
    parser.add_argument("--save-csv", type=Path, default=None,
                        help="Зберегти знайдені match_id в CSV файл")
    parser.add_argument("--rate-limit", type=float, default=1.5,
                        help="Секунд між запитами (default: 1.5)")

    args = parser.parse_args()

    init_db()

    # Discovery
    match_ids = discover_matches(
        count=args.count,
        rank_tier=args.rank_tier,
        region=args.region,
        patch=args.patch,
        lobby_type=args.lobby_type,
    )

    if not match_ids:
        logger.warning("No matches found. Check your filters.")
        sys.exit(0)

    # Опційно зберегти CSV
    if args.save_csv:
        save_to_csv(match_ids, args.save_csv)

    # Якщо --no-ingest — зупиняємось після discovery
    if args.no_ingest:
        logger.info("--no-ingest flag set. Stopping after discovery.")
        sys.exit(0)

    # Ingest
    stats = run_ingest(
        match_ids,
        skip_known=args.skip_known,
        dry_run=args.dry_run,
        rate_limit_sec=args.rate_limit,
    )

    logger.info(
        "Ingest done: ingested=%d skipped=%d failed=%d",
        stats["ingested"], stats["skipped"], stats["failed"],
    )

    if stats["errors"]:
        logger.warning("Failures:")
        for mid, err in stats["errors"]:
            logger.warning("  %d: %s", mid, err)

    # Rebuild
    if args.rebuild and not args.dry_run and stats["ingested"] > 0:
        logger.info("Running rebuild...")
        result = rebuild_all_computed()
        logger.info("Rebuild: %s", result)

    sys.exit(0 if stats["failed"] == 0 else 1)


if __name__ == "__main__":
    main()