#!/usr/bin/env python
# scripts/discover_and_ingest.py
"""Розширений discovery + ingest з гнучкими фільтрами.

Використання:
    # Матчі за останній тиждень, Divine+
    python scripts/discover_and_ingest.py --count 200 --rank-tier 70 --days 7

    # Матчі перед конкретним матчем (хронологічно)
    python scripts/discover_and_ingest.py --count 200 --before-match 8714955447

    # Immortal (Titan) матчі за останні 3 дні
    python scripts/discover_and_ingest.py --count 500 --rank-tier 80 --days 3 --rebuild

    # Тільки discovery — зберегти в CSV
    python scripts/discover_and_ingest.py --count 500 --save-csv found.csv --no-ingest

Rank Tier:
    10=Herald, 20=Guardian, 30=Crusader, 40=Archon,
    50=Legend, 60=Ancient, 70=Divine, 75=Divine/Immortal (Titan), 80=Immortal

Примітка: OpenDota Explorer не підтримує фільтри по region/patch (видалені з public_matches).
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

import requests
from requests.exceptions import RequestException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

RANK_NAMES = {
    10: "Herald", 20: "Guardian", 30: "Crusader", 40: "Archon",
    50: "Legend", 60: "Ancient", 70: "Divine", 75: "Divine/Immortal", 80: "Immortal",
}

MAX_EXPLORER_LIMIT = 200  # batch size для Explorer API


def get_rank_label(tier: int) -> str:
    base = (tier // 10) * 10
    return RANK_NAMES.get(tier) or RANK_NAMES.get(base, f"Tier {tier}")


def is_known(match_id: int) -> bool:
    with UnitOfWork() as uow:
        return IngestionLogRepository(uow.conn).is_known(match_id)


def _get_match_start_time(match_id: int) -> int | None:
    """Отримує start_time матчу з OpenDota API для --before-match фільтра."""
    try:
        url = f"https://api.opendota.com/api/matches/{match_id}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json().get("start_time")
    except Exception as e:
        logger.warning("Не вдалося отримати start_time для матчу %d: %s", match_id, e)
        return None


def fetch_with_retry(url: str, params: dict, retries: int = 3, delay: float = 2.0):
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except RequestException as e:
            logger.warning("Attempt %d failed: %s", attempt, e)
            if attempt < retries:
                time.sleep(delay)
            else:
                raise


def discover_matches(
    count: int,
    rank_tier: int,
    lobby_type: int,
    start_time_after: int | None = None,
    start_time_before: int | None = None,
) -> list[int]:
    """Discovery через OpenDota Explorer з batch та retry. Повертає список match_id."""
    client = OpenDotaExplorerClient()
    match_ids: list[int] = []
    remaining = count

    while remaining > 0:
        batch_limit = min(remaining, MAX_EXPLORER_LIMIT)
        f = DiscoveryFilter(
            lobby_type=lobby_type,
            min_rank_tier=rank_tier,
            limit=batch_limit,
        )

        # time-фільтри через SQL, якщо задані
        if start_time_after or start_time_before:
            from services.ingestion.domains.discovery.query_builder import build_explorer_sql
            base_sql = build_explorer_sql(f)
            extra_conditions = []
            if start_time_after:
                extra_conditions.append(f"start_time >= {start_time_after}")
            if start_time_before:
                extra_conditions.append(f"start_time <= {start_time_before}")
            conditions_str = " AND ".join(extra_conditions)
            if "WHERE" in base_sql:
                sql = base_sql.replace("ORDER BY", f"AND {conditions_str} ORDER BY")
            else:
                sql = base_sql.replace("ORDER BY", f"WHERE {conditions_str} ORDER BY")

            url = "https://api.opendota.com/api/explorer"
            logger.info("Explorer SQL (batch %d): %s", batch_limit, sql)
            data = fetch_with_retry(url, {"sql": sql})
            rows = data.get("rows", [])
            batch_ids = [r["match_id"] for r in rows if "match_id" in r]
        else:
            logger.info(
                "Discovering batch %d | rank=%s",
                batch_limit, get_rank_label(rank_tier)
            )
            discovered = client.discover(f)
            batch_ids = [m.match_id for m in discovered]

        if not batch_ids:
            logger.info("No more matches returned by Explorer, stopping batch discovery.")
            break

        match_ids.extend(batch_ids)
        remaining -= len(batch_ids)
        logger.info("Batch added %d matches, remaining=%d", len(batch_ids), remaining)

        # Невелика пауза між batch
        if remaining > 0:
            time.sleep(1.0)

    logger.info(
        "Total discovered %d match_ids | rank=%s | time_filter=%s",
        len(match_ids),
        get_rank_label(rank_tier),
        f"after={start_time_after} before={start_time_before}" if (start_time_after or start_time_before) else "none",
    )

    return match_ids[:count]


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

    parser.add_argument("--count", type=int, default=100,
                        help="Кількість матчів (default: 100)")
    parser.add_argument("--rank-tier", type=int, default=70,
                        help="Мінімальний rank tier: 70=Divine+, 75=Titan+, 80=Immortal+ (default: 70)")
    parser.add_argument("--lobby-type", type=int, default=7,
                        help="7=ranked (default: 7)")

    # Часові фільтри
    parser.add_argument("--days", type=int, default=None,
                        help="Матчі за останні N днів (default: без обмеження)")
    parser.add_argument("--before-match", type=int, default=None,
                        help="Матчі що відбулись до цього match_id (за start_time)")

    # Поведінка
    parser.add_argument("--skip-known", dest="skip_known", action="store_true", default=True)
    parser.add_argument("--no-skip-known", dest="skip_known", action="store_false")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-ingest", action="store_true")
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--save-csv", type=Path, default=None)
    parser.add_argument("--rate-limit", type=float, default=1.5)

    args = parser.parse_args()

    init_db()

    # Обчислюємо time фільтри
    start_time_after: int | None = None
    start_time_before: int | None = None

    if args.days is not None:
        start_time_after = int(time.time()) - args.days * 86400
        logger.info("Time filter: last %d days (after unix=%d)", args.days, start_time_after)

    if args.before_match is not None:
        logger.info("Fetching start_time for match %d...", args.before_match)
        ts = _get_match_start_time(args.before_match)
        if ts:
            start_time_before = ts
            logger.info("Will fetch matches before %d (unix=%d)", args.before_match, ts)
        else:
            logger.warning("Could not get start_time for match %d — ignoring --before-match", args.before_match)

    # Discovery
    match_ids = discover_matches(
        count=args.count,
        rank_tier=args.rank_tier,
        lobby_type=args.lobby_type,
        start_time_after=start_time_after,
        start_time_before=start_time_before,
    )

    if not match_ids:
        logger.warning("No matches found.")
        sys.exit(0)

    if args.save_csv:
        save_to_csv(match_ids, args.save_csv)

    if args.no_ingest:
        logger.info("--no-ingest flag set. Stopping after discovery.")
        sys.exit(0)

    stats = run_ingest(
        match_ids,
        skip_known=args.skip_known,
        dry_run=args.dry_run,
        rate_limit_sec=args.rate_limit,
    )

    logger.info(
        "Done: ingested=%d skipped=%d failed=%d",
        stats["ingested"], stats["skipped"], stats["failed"],
    )

    if stats["errors"]:
        logger.warning("Failures:")
        for mid, err in stats["errors"]:
            logger.warning("  %d: %s", mid, err)

    if args.rebuild and not args.dry_run and stats["ingested"] > 0:
        logger.info("Running rebuild...")
        result = rebuild_all_computed()
        logger.info("Rebuild: %s", result)

    sys.exit(0 if stats["failed"] == 0 else 1)


if __name__ == "__main__":
    main()