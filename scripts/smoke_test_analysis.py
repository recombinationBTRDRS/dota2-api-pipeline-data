#!/usr/bin/env python
# scripts/smoke_test_analysis.py
"""
Smoke test для Analysis сервісу (Task 8.12).

Потребує:
  - Ingestion API запущений на :8000  (uvicorn services.ingestion.app.main:app --port 8000)
  - Analysis API запущений на :8001   (uvicorn services.analysis.app.main:app --port 8001)
  - Хоча б 1 матч в Ingestion DB

Запуск:
  python scripts/smoke_test_analysis.py
  python scripts/smoke_test_analysis.py --match-id 8714955447
"""
import argparse
import json
import sys
import time

import requests

INGESTION = "http://localhost:8000"
ANALYSIS  = "http://localhost:8001"
TIMEOUT   = 15


# ── helpers ───────────────────────────────────────────────────────────────────

ok_count   = 0
fail_count = 0


def ok(msg: str) -> None:
    global ok_count
    ok_count += 1
    print(f"  ✅ {msg}")


def fail(msg: str) -> None:
    global fail_count
    fail_count += 1
    print(f"  ❌ {msg}")


def section(title: str) -> None:
    print(f"\n{'─' * 55}")
    print(f"  {title}")
    print(f"{'─' * 55}")


def get(url: str) -> requests.Response:
    return requests.get(url, timeout=TIMEOUT)


def post(url: str, **kwargs) -> requests.Response:
    return requests.post(url, timeout=TIMEOUT, **kwargs)


def delete(url: str) -> requests.Response:
    return requests.delete(url, timeout=TIMEOUT)


# ── steps ─────────────────────────────────────────────────────────────────────

def step_health() -> None:
    section("1. Health checks")
    for name, url in [("Ingestion", INGESTION), ("Analysis", ANALYSIS)]:
        try:
            r = get(f"{url}/health")
            if r.status_code == 200 and r.json().get("db_ok"):
                ok(f"{name} /health → ok")
            else:
                fail(f"{name} /health → {r.status_code} {r.text[:80]}")
        except Exception as e:
            fail(f"{name} /health → connection error: {e}")


def step_get_match_id() -> int | None:
    """Отримати реальний match_id з Ingestion DB."""
    section("2. Get real match_id from Ingestion")
    try:
        # Беремо перший матч з /analytics/meta (list heroes) або через smoke check
        # Ingestion не має /matches endpoint — дістаємо через hero stats
        r = get(f"{INGESTION}/computed/heroes/top?limit=1")
        if r.status_code != 200:
            fail(f"GET /computed/heroes/top → {r.status_code}")
            return None
        ok(f"Ingestion /computed/heroes/top → {r.status_code}")
    except Exception as e:
        fail(f"Ingestion unavailable: {e}")
        return None
    return None  # match_id буде передано аргументом


def step_ingestion_data(match_id: int) -> None:
    section("3. Verify Ingestion pre-computed data")

    # matchups для першого героя
    try:
        r = get(f"{INGESTION}/computed/heroes/1/matchups?limit=5")
        if r.status_code == 200:
            data = r.json()
            ok(f"Hero 1 matchups → {len(data)} записів")
        else:
            fail(f"Hero 1 matchups → {r.status_code}")
    except Exception as e:
        fail(f"Hero matchups error: {e}")

    # synergies
    try:
        r = get(f"{INGESTION}/computed/heroes/1/synergies?limit=5")
        if r.status_code == 200:
            data = r.json()
            ok(f"Hero 1 synergies → {len(data)} записів")
        else:
            fail(f"Hero 1 synergies → {r.status_code}")
    except Exception as e:
        fail(f"Hero synergies error: {e}")

    # hero stats
    try:
        r = get(f"{INGESTION}/computed/heroes/1/stats")
        if r.status_code == 200:
            ok("Hero 1 stats → ok")
        else:
            fail(f"Hero 1 stats → {r.status_code}")
    except Exception as e:
        fail(f"Hero stats error: {e}")


def step_watchlist(match_id: int) -> bool:
    section(f"4. Watchlist CRUD (match_id={match_id})")

    # Cleanup якщо залишився з попереднього запуску
    delete(f"{ANALYSIS}/watchlist/matches/{match_id}")

    # POST
    try:
        r = post(
            f"{ANALYSIS}/watchlist/matches",
            json={"match_id": match_id, "label": "smoke-test"},
        )
        if r.status_code == 201:
            ok(f"POST /watchlist/matches → 201, status={r.json()['status']}")
        else:
            fail(f"POST /watchlist/matches → {r.status_code} {r.text[:80]}")
            return False
    except Exception as e:
        fail(f"POST watchlist error: {e}")
        return False

    # GET list
    try:
        r = get(f"{ANALYSIS}/watchlist/matches")
        items = r.json()
        found = any(i["match_id"] == match_id for i in items)
        if found:
            ok(f"GET /watchlist/matches → match_id знайдений у списку")
        else:
            fail("GET /watchlist/matches → match_id не знайдений")
    except Exception as e:
        fail(f"GET watchlist error: {e}")

    # GET single
    try:
        r = get(f"{ANALYSIS}/watchlist/matches/{match_id}")
        if r.status_code == 200:
            ok(f"GET /watchlist/matches/{match_id} → 200")
        else:
            fail(f"GET /watchlist/matches/{match_id} → {r.status_code}")
    except Exception as e:
        fail(f"GET single watchlist error: {e}")

    return True


def step_generate_report(match_id: int) -> dict | None:
    section(f"5. Generate report (match_id={match_id})")
    try:
        r = post(f"{ANALYSIS}/reports/matches/{match_id}")
        if r.status_code == 200:
            data = r.json()
            ok(f"POST /reports/matches/{match_id} → 200")
            ok(f"data_quality={data.get('data_quality')}")
            return data
        else:
            fail(f"POST /reports → {r.status_code} {r.text[:120]}")
            return None
    except Exception as e:
        fail(f"POST report error: {e}")
        return None


def step_check_report(match_id: int, report: dict) -> None:
    section("6. Verify report fields")

    # teamfight (не потребує match_players — рахується завжди якщо є гравці)
    tf = report.get("teamfight")
    if tf:
        ok(f"teamfight → verdict={tf['teamfight_verdict']}, "
           f"r_kills={tf['radiant_kills']}, d_kills={tf['dire_kills']}")
    else:
        # teamfight може бути None якщо get_match_players не реалізовано
        print(f"  ⚠️  teamfight=None (get_match_players не реалізовано в Ingestion — очікувано)")

    economy = report.get("economy")
    if economy:
        ok(f"economy → advantage={economy['networth_advantage']}, "
           f"r_gpm={economy['radiant_avg_gpm']}, d_gpm={economy['dire_avg_gpm']}")
    else:
        print(f"  ⚠️  economy=None (get_match_players не реалізовано — очікувано)")

    draft = report.get("draft")
    if draft:
        ok(f"draft → overall={draft.get('overall')}, quality={draft['data_quality']}")
    else:
        print(f"  ⚠️  draft=None (get_match_players не реалізовано — очікувано)")


def step_get_saved_report(match_id: int) -> None:
    section("7. GET saved report")
    try:
        r = get(f"{ANALYSIS}/reports/matches/{match_id}")
        if r.status_code == 200:
            ok(f"GET /reports/matches/{match_id} → 200, збережений звіт отримано")
        else:
            fail(f"GET /reports → {r.status_code}")
    except Exception as e:
        fail(f"GET report error: {e}")


def step_watchlist_status(match_id: int) -> None:
    section("8. Watchlist status after report")
    try:
        r = get(f"{ANALYSIS}/watchlist/matches/{match_id}")
        status = r.json().get("status")
        if status == "analyzed":
            ok(f"watchlist status → 'analyzed' ✓")
        else:
            fail(f"watchlist status → '{status}' (очікувалось 'analyzed')")
    except Exception as e:
        fail(f"Watchlist status check error: {e}")


def step_cleanup(match_id: int) -> None:
    section("9. Cleanup")
    try:
        r = delete(f"{ANALYSIS}/watchlist/matches/{match_id}")
        if r.status_code == 204:
            ok(f"DELETE /watchlist/matches/{match_id} → 204")
        else:
            fail(f"DELETE → {r.status_code}")
    except Exception as e:
        fail(f"Cleanup error: {e}")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test for Analysis service")
    parser.add_argument(
        "--match-id", type=int, default=8714955447,
        help="Match ID to use for smoke test (default: 8714955447)"
    )
    args = parser.parse_args()
    match_id = args.match_id

    print("=" * 55)
    print("  Smoke Test — Analysis Service (Task 8.12)")
    print(f"  match_id = {match_id}")
    print("=" * 55)

    step_health()
    step_ingestion_data(match_id)

    in_watchlist = step_watchlist(match_id)
    if not in_watchlist:
        print("\n❌ Watchlist step failed — aborting")
        sys.exit(1)

    report = step_generate_report(match_id)
    if report:
        step_check_report(match_id, report)
        step_get_saved_report(match_id)
        step_watchlist_status(match_id)

    step_cleanup(match_id)

    # ── summary ───────────────────────────────────────────────────────────────
    print(f"\n{'=' * 55}")
    print(f"  RESULTS: {ok_count} ✅  |  {fail_count} ❌")
    print(f"{'=' * 55}\n")

    if fail_count > 0:
        sys.exit(1)
    else:
        print("  🎉 All smoke tests passed!\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
