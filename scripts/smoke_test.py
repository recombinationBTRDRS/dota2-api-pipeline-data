#!/usr/bin/env python
# scripts/smoke_test.py
"""R1.4 — Smoke test на реальних даних OpenDota API.

Запуск:
    python scripts/smoke_test.py

Повертає exit code 1 якщо є failures.
"""
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

MATCH_ID = 8_709_253_716

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

    # DB_PATH підміняється тут — не на рівні імпорту
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
    print("  Dota 2 Pipeline — R1.4 Smoke Test")
    print(f"  DB: {TEST_DB}")
    print(f"  Match: {MATCH_ID}")
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
            fail(f"Завантажено {count} героїв — очікувалось >= 120")
            failures.append(f"sync_heroes: {count} < 120")

        with UnitOfWork() as uow:
            am = uow.conn.execute(
                "SELECT id, name FROM heroes WHERE name LIKE '%antimage%'"
            ).fetchone()
            if am:
                ok(f"Anti-Mage: id={am['id']} ✓")
            else:
                fail("Anti-Mage не знайдений")
                failures.append("Anti-Mage not found")

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
    section(f"4. ingest_match({MATCH_ID})")
    try:
        from services.ingestion.app.ingest_match import ingest_match
        ingest_match(MATCH_ID)
        ok(f"Матч {MATCH_ID} інгестовано")

        with UnitOfWork() as uow:
            conn = uow.conn

            match_row = conn.execute(
                "SELECT id, duration, radiant_win, patch, region FROM matches WHERE id = ?",
                (MATCH_ID,),
            ).fetchone()

            if not match_row:
                fail("Матч не знайдений в matches")
                failures.append("match not in DB")
            else:
                ok(f"duration={match_row['duration']}s, radiant_win={bool(match_row['radiant_win'])}")

                if match_row["patch"] is not None:
                    ok(f"patch={match_row['patch']} ✓")
                else:
                    fail("patch is NULL — BL1.1 regression")
                    failures.append("patch is NULL")

                if match_row["region"] is not None:
                    ok(f"region={match_row['region']} ✓")
                else:
                    fail("region is NULL — BL1.1 regression")
                    failures.append("region is NULL")

            mp_count = conn.execute(
                "SELECT COUNT(*) FROM match_players WHERE match_id = ?", (MATCH_ID,),
            ).fetchone()[0]
            if mp_count == 10:
                ok(f"match_players: {mp_count}/10 ✓")
            else:
                fail(f"match_players: {mp_count} (очікувалось 10)")
                failures.append(f"match_players count={mp_count}")

            # lane_role — warn тільки (залежить від парсингу replay, не від нас)
            players = conn.execute(
                "SELECT mp.player_slot, h.localized_name, mp.lane_role, "
                "mp.is_roaming, mp.win, mp.gpm, mp.kills "
                "FROM match_players mp LEFT JOIN heroes h ON h.id = mp.hero_id "
                "WHERE mp.match_id = ? ORDER BY mp.player_slot", (MATCH_ID,),
            ).fetchall()

            lane_nulls = sum(1 for p in players if p["lane_role"] is None)
            if lane_nulls == 0:
                ok(f"lane_role заповнений для всіх {len(players)} гравців ✓")
            else:
                warn(f"lane_role NULL для {lane_nulls}/{len(players)} — матч не парсений (OK)")

            print()
            print(f"  {'slot':>4}  {'hero':<22}  {'lane':>4}  {'roam':>5}  "
                  f"{'win':>5}  {'gpm':>4}  {'kills':>5}")
            print(f"  {'─'*4}  {'─'*22}  {'─'*4}  {'─'*5}  {'─'*5}  {'─'*4}  {'─'*5}")
            for p in players:
                name = (p["localized_name"] or "?")[:22]
                print(f"  {p['player_slot']:>4}  {name:<22}  "
                      f"{str(p['lane_role']):>4}  {str(bool(p['is_roaming'])):>5}  "
                      f"{str(bool(p['win'])):>5}  {p['gpm']:>4}  {p['kills']:>5}")

            anon = conn.execute(
                "SELECT COUNT(*) FROM players WHERE account_id = 4294967295"
            ).fetchone()[0]
            if anon == 0:
                ok("account_id sentinel не в DB ✓")
            else:
                fail(f"{anon} гравців з account_id=4294967295")
                failures.append(f"anonymous sentinel: {anon}")

            items_count = conn.execute(
                "SELECT COUNT(*) FROM match_player_items WHERE match_id = ?", (MATCH_ID,),
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

    # ── 5. Analytics ──────────────────────────────────────────────────────────
    section("5. Analytics queries")
    try:
        with UnitOfWork() as uow:
            conn = uow.conn
            from services.ingestion.db.repositories.analytics.hero_stats import HeroStatsRepository
            from services.ingestion.db.repositories.analytics.timeline import (
                MatchTimelineRepository,
            )

            hero_row = conn.execute(
                "SELECT mp.hero_id, h.localized_name FROM match_players mp "
                "LEFT JOIN heroes h ON h.id = mp.hero_id WHERE mp.match_id = ? LIMIT 1",
                (MATCH_ID,),
            ).fetchone()
            hid = hero_row["hero_id"] if hero_row else 1
            hname = (hero_row["localized_name"] or str(hid)) if hero_row else "?"

            stats = HeroStatsRepository(conn).get_hero_stats(hid)
            if stats:
                ok(f"HeroStats {hname}: matches={stats.matches_played}, "
                   f"wr={stats.winrate}, gpm={stats.avg_gpm}")
            else:
                warn(f"HeroStats: немає даних для {hname}")

            meta = MatchTimelineRepository(conn).get_meta_snapshot(limit=5)
            if meta:
                ok("MetaSnapshot топ-5:")
                for m in meta:
                    info(f"  {m.hero_name:<25} pos={m.primary_pos} "
                         f"wr={m.winrate:.3f} meta={m.meta_score}")
            else:
                warn("MetaSnapshot: порожньо (замало матчів)")

            tl = MatchTimelineRepository(conn).get_hero_phase_stats(hid)
            if tl:
                ok(f"Timeline {hname}: {[t.phase for t in tl]}")
            else:
                warn(f"Timeline: немає даних для {hname}")

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