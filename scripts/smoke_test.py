#!/usr/bin/env python
# scripts/smoke_test.py
"""Smoke test на реальних даних OpenDota API.

Запуск:
    python scripts/smoke_test.py

Повертає exit code 1 якщо є failures.
"""
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

MATCH_ID  = 8_709_253_716
MATCH_ID2 = 8_714_955_447   # другий матч для matchup/synergy (потрібно 2+ матчі)

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "
INFO = "   "


def section(title: str) -> None:
    print(f"\n{'─' * 55}\n  {title}\n{'─' * 55}")

def ok(msg: str) -> None:   print(f"  {PASS}  {msg}")
def fail(msg: str) -> None: print(f"  {FAIL}  {msg}")
def warn(msg: str) -> None: print(f"  {WARN} {msg}")
def info(msg: str) -> None: print(f"  {INFO}  {msg}")


def main() -> None:
    import services.ingestion.db.sqlite as sqlite_module

    TEST_DB = ROOT / "services" / "ingestion" / "db" / "smoke_test.sqlite"
    orig_db_path = sqlite_module.DB_PATH
    sqlite_module.DB_PATH = TEST_DB

    try:
        _run(TEST_DB, sqlite_module)
    finally:
        sqlite_module.DB_PATH = orig_db_path
        if TEST_DB.exists():
            TEST_DB.unlink()
            info("smoke_test.sqlite видалено")


def _run(TEST_DB: Path, sqlite_module: object) -> None:
    from services.ingestion.db.sqlite import init_db
    from services.ingestion.db.unit_of_work import UnitOfWork

    failures: list[str] = []

    print(f"\n{'═' * 55}")
    print("  Dota 2 Pipeline — Smoke Test (Epic 7)")
    print(f"  DB: {TEST_DB}")
    print(f"  Match 1: {MATCH_ID}  Match 2: {MATCH_ID2}")
    print(f"{'═' * 55}")

    # ── 0. Init DB ────────────────────────────────────────────────────────────
    section("0. Init DB")
    try:
        if TEST_DB.exists():
            TEST_DB.unlink()
            info("Видалено стару smoke_test.sqlite")
        init_db()
        ok("DB ініціалізована")
    except Exception as e:
        fail(f"init_db() failed: {e}")
        traceback.print_exc()
        sys.exit(1)

    # ── 1. sync_heroes ────────────────────────────────────────────────────────
    section("1. sync_heroes()")
    try:
        from services.ingestion.app.sync_heroes import sync_heroes
        count = sync_heroes()
        if count >= 120:
            ok(f"Завантажено {count} героїв")
        else:
            fail(f"Завантажено {count} — очікувалось >= 120")
            failures.append(f"sync_heroes: {count} < 120")

        with UnitOfWork() as uow:
            am = uow.conn.execute(
                "SELECT id FROM heroes WHERE name LIKE '%antimage%'"
            ).fetchone()
            ok(f"Anti-Mage: id={am['id']} ✓") if am else (
                fail("Anti-Mage не знайдений") or failures.append("Anti-Mage not found")
            )
    except Exception as e:
        fail(f"sync_heroes() crashed: {e}")
        traceback.print_exc()
        failures.append(f"sync_heroes crashed: {e}")

    # ── 2. sync_items ─────────────────────────────────────────────────────────
    section("2. sync_items()")
    try:
        from services.ingestion.app.sync_items import sync_items
        count = sync_items()
        if count >= 200:
            ok(f"Завантажено {count} items")
        else:
            fail(f"Завантажено {count} — очікувалось >= 200")
            failures.append(f"sync_items: {count} < 200")
    except Exception as e:
        fail(f"sync_items() crashed: {e}")
        traceback.print_exc()
        failures.append(f"sync_items crashed: {e}")

    # ── 3. sync_role_scores ───────────────────────────────────────────────────
    section("3. sync_role_scores()")
    try:
        from services.ingestion.app.sync_role_scores import sync_role_scores
        count = sync_role_scores()
        if count >= 120:
            ok(f"Збережено {count} role score записів")
        else:
            fail(f"Збережено {count} — очікувалось >= 120")
            failures.append(f"sync_role_scores: {count} < 120")

        with UnitOfWork() as uow:
            missing = uow.conn.execute(
                "SELECT h.localized_name FROM heroes h "
                "WHERE NOT EXISTS (SELECT 1 FROM hero_role_scores WHERE hero_id = h.id)"
            ).fetchall()
            if missing:
                warn(f"{len(missing)} героїв без role scores: "
                     f"{[r['localized_name'] for r in missing]}")
            else:
                ok("Всі герої мають role scores ✓")
    except Exception as e:
        fail(f"sync_role_scores() crashed: {e}")
        traceback.print_exc()
        failures.append(f"sync_role_scores crashed: {e}")

    # ── 4. ingest_match ───────────────────────────────────────────────────────
    section("4. ingest_match (2 матчі)")
    try:
        from services.ingestion.app.ingest_match import ingest_match

        for mid in (MATCH_ID, MATCH_ID2):
            try:
                ingest_match(mid)
                ok(f"Матч {mid} інгестовано")
            except Exception as e:
                fail(f"Матч {mid} не інгестовано: {e}")
                traceback.print_exc()
                failures.append(f"ingest failed match={mid}")

        with UnitOfWork() as uow:
            conn = uow.conn

            for mid in (MATCH_ID, MATCH_ID2):
                row = conn.execute(
                    "SELECT duration, patch, region FROM matches WHERE id = ?", (mid,)
                ).fetchone()
                if not row:
                    fail(f"Матч {mid} не в matches")
                    failures.append(f"match {mid} not in DB")
                    continue

                ok(f"Match {mid}: duration={row['duration']}s")

                if row["patch"] is not None:
                    ok(f"  patch={row['patch']} ✓")
                else:
                    fail(f"  patch is NULL для {mid}")
                    failures.append(f"patch NULL match={mid}")

                if row["region"] is not None:
                    ok(f"  region={row['region']} ✓")
                else:
                    fail(f"  region is NULL для {mid}")
                    failures.append(f"region NULL match={mid}")

                mp_count = conn.execute(
                    "SELECT COUNT(*) FROM match_players WHERE match_id = ?", (mid,)
                ).fetchone()[0]
                if mp_count == 10:
                    ok("  match_players: 10/10 ✓")
                else:
                    fail(f"  match_players: {mp_count} (очікувалось 10)")
                    failures.append(f"match_players count={mp_count} match={mid}")

                # Task 7.3 — перевірка radiant/dire
                radiant = conn.execute(
                    "SELECT COUNT(*) FROM match_players WHERE match_id = ? AND player_slot < 128",
                    (mid,)
                ).fetchone()[0]
                dire = conn.execute(
                    "SELECT COUNT(*) FROM match_players WHERE match_id = ? AND player_slot >= 128",
                    (mid,)
                ).fetchone()[0]
                if radiant == 5 and dire == 5:
                    ok(f"  player_slot: radiant={radiant} dire={dire} ✓")
                else:
                    fail(f"  player_slot: radiant={radiant} dire={dire} (очікувалось 5/5)")
                    failures.append(f"player_slot split radiant={radiant} dire={dire} match={mid}")

            # Task 7.6 — performance fields
            perf = conn.execute(
                "SELECT net_worth, hero_damage, last_hits "
                "FROM match_players WHERE match_id = ? LIMIT 1", (MATCH_ID2,)
            ).fetchone()
            if perf and any(v is not None for v in perf):
                ok(f"Performance fields: net_worth={perf['net_worth']} "
                   f"hero_damage={perf['hero_damage']} last_hits={perf['last_hits']} ✓")
            else:
                warn("Performance fields NULL — матч не парсений OpenDota (OK)")

            # lane_role
            players = conn.execute(
                "SELECT player_slot, lane_role FROM match_players WHERE match_id = ?",
                (MATCH_ID,)
            ).fetchall()
            lane_nulls = sum(1 for p in players if p["lane_role"] is None)
            if lane_nulls == 0:
                ok("lane_role заповнений для всіх гравців ✓")
            else:
                warn(f"lane_role NULL для {lane_nulls}/10 — матч не парсений (OK)")

            # anonymous sentinel
            anon = conn.execute(
                "SELECT COUNT(*) FROM players WHERE account_id = 4294967295"
            ).fetchone()[0]
            if anon == 0:
                ok("account_id sentinel не в DB ✓")
            else:
                fail(f"{anon} гравців з account_id=4294967295")
                failures.append(f"anonymous sentinel: {anon}")

            items_count = conn.execute(
                "SELECT COUNT(*) FROM match_player_items WHERE match_id = ?", (MATCH_ID,)
            ).fetchone()[0]
            if items_count > 0:
                ok(f"match_player_items: {items_count} записів ✓")
            else:
                fail("match_player_items: 0 записів")
                failures.append("match_player_items empty")

    except Exception as e:
        fail(f"ingest_match() crashed: {e}")
        traceback.print_exc()
        failures.append(f"ingest_match crashed: {e}")

    # ── 5. Rebuild pre-computed ───────────────────────────────────────────────
    section("5. Rebuild pre-computed tables")
    try:
        from services.ingestion.app.rebuild_all import rebuild_all_computed
        result = rebuild_all_computed()

        checks = [
            ("hero_stats_rows",  result.get("hero_stats_rows",  0), 1),
            ("item_build_rows",  result.get("item_build_rows",  0), 1),
            ("matchup_rows",     result.get("matchup_rows",     0), 1),
            ("synergy_rows",     result.get("synergy_rows",     0), 1),
        ]
        for name, val, min_val in checks:
            if val >= min_val:
                ok(f"{name}: {val} ✓")
            else:
                fail(f"{name}: {val} (очікувалось >= {min_val})")
                failures.append(f"{name}={val}")

    except Exception as e:
        fail(f"rebuild_all_computed() crashed: {e}")
        traceback.print_exc()
        failures.append(f"rebuild crashed: {e}")

    # ── 6. Analytics + Matchup/Synergy ────────────────────────────────────────
    section("6. Analytics + Matchup/Synergy queries")
    try:
        with UnitOfWork() as uow:
            conn = uow.conn

            from services.ingestion.db.repositories.analytics.hero_stats import HeroStatsRepository
            from services.ingestion.db.repositories.analytics.matchup import MatchupRepository
            from services.ingestion.db.repositories.analytics.timeline import (
                MatchTimelineRepository,
            )

            hero_row = conn.execute(
                "SELECT mp.hero_id, h.localized_name FROM match_players mp "
                "LEFT JOIN heroes h ON h.id = mp.hero_id WHERE mp.match_id = ? LIMIT 1",
                (MATCH_ID,),
            ).fetchone()
            hid   = hero_row["hero_id"] if hero_row else 1
            hname = (hero_row["localized_name"] or str(hid)) if hero_row else "?"

            stats = HeroStatsRepository(conn).get_hero_stats(hid)
            if stats:
                ok(f"HeroStats {hname}: matches={stats.matches_played} wr={stats.winrate}")
            else:
                warn(f"HeroStats: немає даних для {hname}")

            meta = MatchTimelineRepository(conn).get_meta_snapshot(limit=5)
            if meta:
                ok(f"MetaSnapshot: {len(meta)} записів ✓")
            else:
                warn("MetaSnapshot: порожньо (замало матчів)")

            # Matchup
            matchup_repo = MatchupRepository(conn)
            counters = matchup_repo.get_hero_matchups(hid, limit=3)
            if counters:
                ok(f"Counters для {hname}: {len(counters)} записів ✓")
                for c in counters:
                    info(f"  vs hero_id={c.opponent_id}: matches={c.matches} "
                         f"winrate={c.winrate:.3f}")
            else:
                warn(f"Counters для {hname}: порожньо (замало матчів)")

            # Synergy
            synergies = matchup_repo.get_hero_synergies(hid, limit=3)
            if synergies:
                ok(f"Synergies для {hname}: {len(synergies)} записів ✓")
                for s in synergies:
                    info(f"  with hero_id={s.ally_id}: matches={s.matches} "
                         f"winrate={s.winrate:.3f}")
            else:
                warn(f"Synergies для {hname}: порожньо (замало матчів)")

    except Exception as e:
        fail(f"Analytics crashed: {e}")
        traceback.print_exc()
        failures.append(f"analytics crashed: {e}")

    # ── Підсумок ──────────────────────────────────────────────────────────────
    section("Підсумок")
    if not failures:
        print(f"\n  {PASS}  Всі перевірки пройшли!\n")
        sys.exit(0)
    else:
        print(f"\n  {FAIL}  {len(failures)} проблем(и):")
        for f in failures:
            print(f"       • {f}")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
