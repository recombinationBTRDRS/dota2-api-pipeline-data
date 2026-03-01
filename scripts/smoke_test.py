#!/usr/bin/env python
# scripts/smoke_test.py
"""R1.4 — Smoke test на реальних даних OpenDota API.

Запуск з кореня проекту:
    python scripts/smoke_test.py
"""
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

TEST_DB = ROOT / "services" / "ingestion" / "db" / "smoke_test.sqlite"
MATCH_ID = 8_709_253_716

import services.ingestion.db.sqlite as sqlite_module  # noqa: E402

sqlite_module.DB_PATH = TEST_DB

from services.ingestion.db.sqlite import init_db  # noqa: E402
from services.ingestion.db.unit_of_work import UnitOfWork  # noqa: E402

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
            warn(f"Завантажено {count} героїв — очікувалось >= 120")
            failures.append(f"sync_heroes: {count} < 120")

        # Діагностика: показуємо перших 5 героїв щоб бачити реальні name/localized_name
        with UnitOfWork() as uow:
            sample = uow.conn.execute(
                "SELECT id, name, localized_name FROM heroes ORDER BY id LIMIT 5"
            ).fetchall()
            info("Перші 5 героїв (id | name | localized_name):")
            for r in sample:
                info(f"  {r['id']:>4}  {r['name']:<30}  {r['localized_name']}")

            # Anti-Mage може мати різні name в різних версіях API
            am = uow.conn.execute(
                "SELECT id, name, localized_name FROM heroes "
                "WHERE name LIKE '%antimage%' OR localized_name LIKE '%Anti%'"
            ).fetchone()
            if am:
                ok(f"Anti-Mage знайдений: id={am['id']}, name='{am['name']}', "
                   f"localized='{am['localized_name']}'")
            else:
                warn("Anti-Mage не знайдений — можлива зміна name в API")
                failures.append("Anti-Mage not found")

            # Скільки героїв без role scores (будуть після sync_role_scores)
            no_role = uow.conn.execute(
                "SELECT COUNT(*) FROM heroes h "
                "WHERE NOT EXISTS (SELECT 1 FROM hero_role_scores WHERE hero_id = h.id)"
            ).fetchone()[0]
            if no_role > 0:
                info(f"{no_role} нових героїв без role scores (очікується після sync_role_scores)")

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
            warn(f"Завантажено {count} items — очікувалось >= 200")
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
        if count >= 100:
            ok(f"Збережено {count} role score записів")
        else:
            warn(f"Збережено {count} — очікувалось >= 100")
            failures.append(f"sync_role_scores: {count} < 100")

        # Покажемо яких героїв немає в HERO_META (нові герої)
        with UnitOfWork() as uow:
            new_heroes = uow.conn.execute(
                "SELECT h.id, h.name, h.localized_name FROM heroes h "
                "WHERE NOT EXISTS "
                "(SELECT 1 FROM hero_role_scores WHERE hero_id = h.id)"
            ).fetchall()
            if new_heroes:
                warn(f"{len(new_heroes)} героїв без role scores (немає в HERO_META):")
                for h in new_heroes:
                    info(f"  id={h['id']} name='{h['name']}' localized='{h['localized_name']}'")
            else:
                ok("Всі герої мають role scores")

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

            if match_row:
                ok(f"matches: duration={match_row['duration']}s, "
                   f"radiant_win={bool(match_row['radiant_win'])}")

                if match_row["patch"] is not None:
                    ok(f"patch={match_row['patch']} ✓")
                else:
                    warn("patch is NULL — OpenDota не повернув це поле")

                if match_row["region"] is not None:
                    ok(f"region={match_row['region']} ✓")
                else:
                    warn("region is NULL — OpenDota не повернув це поле")
            else:
                fail("Матч не знайдений в matches table")
                failures.append("match not in DB")

            # match_players
            mp_count = conn.execute(
                "SELECT COUNT(*) FROM match_players WHERE match_id = ?",
                (MATCH_ID,),
            ).fetchone()[0]
            if mp_count == 10:
                ok(f"match_players: {mp_count}/10 гравців ✓")
            else:
                warn(f"match_players: {mp_count} гравців (очікувалось 10)")
                failures.append(f"match_players count={mp_count}")

            # lane_role/is_roaming таблиця
            players = conn.execute(
                "SELECT mp.player_slot, mp.hero_id, h.localized_name, "
                "mp.lane_role, mp.is_roaming, mp.win, mp.gpm, mp.kills "
                "FROM match_players mp "
                "LEFT JOIN heroes h ON h.id = mp.hero_id "
                "WHERE mp.match_id = ? ORDER BY mp.player_slot",
                (MATCH_ID,),
            ).fetchall()

            lane_nulls = sum(1 for p in players if p["lane_role"] is None)
            if lane_nulls == 0:
                ok(f"lane_role заповнений для всіх {len(players)} гравців ✓")
            else:
                warn(f"lane_role is NULL для {lane_nulls}/{len(players)} гравців")

            print()
            print(f"  {'slot':>4}  {'hero':<22}  {'lane':>4}  {'roam':>5}  "
                  f"{'win':>4}  {'gpm':>4}  {'kills':>5}")
            print(f"  {'─'*4}  {'─'*22}  {'─'*4}  {'─'*5}  {'─'*4}  {'─'*4}  {'─'*5}")
            for p in players:
                name = (p["localized_name"] or f"id={p['hero_id']}")[:22]
                print(f"  {p['player_slot']:>4}  {name:<22}  "
                      f"{str(p['lane_role']):>4}  {str(bool(p['is_roaming'])):>5}  "
                      f"{str(bool(p['win'])):>4}  {p['gpm']:>4}  {p['kills']:>5}")

            # account_id sentinel check
            anon_sentinel = conn.execute(
                "SELECT COUNT(*) FROM players WHERE account_id = 4294967295"
            ).fetchone()[0]
            if anon_sentinel == 0:
                ok("account_id=4294967295 не потрапив в DB ✓")
            else:
                fail(f"{anon_sentinel} гравців з account_id=4294967295 в players")
                failures.append(f"anonymous sentinel in players: {anon_sentinel}")

            # items
            items_count = conn.execute(
                "SELECT COUNT(*) FROM match_player_items WHERE match_id = ?",
                (MATCH_ID,),
            ).fetchone()[0]
            if items_count > 0:
                ok(f"match_player_items: {items_count} записів ✓")
            else:
                warn("match_player_items: 0 записів")

    except Exception as e:
        fail(f"ingest_match() crashed: {e}")
        traceback.print_exc()
        failures.append(f"ingest_match crashed: {e}")

    # ── 5. Analytics ──────────────────────────────────────────────────────────
    section("5. Analytics queries")
    try:
        with UnitOfWork() as uow:
            conn = uow.conn

            from services.ingestion.db.repositories.analytics.hero_stats import (
                HeroStatsRepository,
            )
            from services.ingestion.db.repositories.analytics.timeline import (
                MatchTimelineRepository,
            )

            hero_row = conn.execute(
                "SELECT mp.hero_id, h.localized_name FROM match_players mp "
                "LEFT JOIN heroes h ON h.id = mp.hero_id "
                "WHERE mp.match_id = ? LIMIT 1",
                (MATCH_ID,),
            ).fetchone()
            test_hero_id = hero_row["hero_id"] if hero_row else 1
            test_hero_name = (hero_row["localized_name"] or str(test_hero_id)) if hero_row else "?"

            stats = HeroStatsRepository(conn).get_hero_stats(test_hero_id)
            if stats:
                ok(f"HeroStats {test_hero_name}: "
                   f"matches={stats.matches_played}, winrate={stats.winrate}, "
                   f"avg_gpm={stats.avg_gpm}")
            else:
                warn(f"HeroStats: немає даних для {test_hero_name}")

            meta = MatchTimelineRepository(conn).get_meta_snapshot(limit=5)
            if meta:
                ok("MetaSnapshot топ-5:")
                for m in meta:
                    info(f"  {m.hero_name:<25} pos={m.primary_pos} "
                         f"wr={m.winrate:.3f} meta={m.meta_score}")
            else:
                warn("MetaSnapshot: порожньо (потрібно більше матчів для role scores)")

            timeline = MatchTimelineRepository(conn).get_hero_phase_stats(test_hero_id)
            if timeline:
                ok(f"Timeline {test_hero_name}: {[t.phase for t in timeline]}")
            else:
                warn(f"Timeline: немає даних для {test_hero_name}")

    except Exception as e:
        fail(f"Analytics crashed: {e}")
        traceback.print_exc()
        failures.append(f"analytics crashed: {e}")

    # ── Підсумок ──────────────────────────────────────────────────────────────
    section("Підсумок")
    if not failures:
        print(f"\n  {PASS}  Всі перевірки пройшли!\n")
    else:
        print(f"\n  {FAIL}  {len(failures)} проблем(и):")
        for f in failures:
            print(f"       • {f}")
        print()

    if TEST_DB.exists():
        TEST_DB.unlink()
        info("smoke_test.sqlite видалено")


if __name__ == "__main__":
    main()