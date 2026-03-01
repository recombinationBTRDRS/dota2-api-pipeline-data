# services/ingestion/tests/db/test_match_timeline_repository.py
"""Unit тести MatchTimelineRepository (Task 4.4).

4.4a — get_hero_phase_stats: early/mid/late winrate по герою.
4.4b — get_meta_snapshot: топ героїв по meta_score.
"""
import pytest

from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.repositories import MatchTimelineRepository
from services.ingestion.db.sqlite import init_db
from services.ingestion.db.unit_of_work import UnitOfWork

# ── fixture + seed helpers ────────────────────────────────────────────────────

@pytest.fixture()
def db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()
    return db_path


def _seed_hero(conn, hero_id: int, name: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO heroes (id, name, localized_name, primary_attr, attack_type) "
        "VALUES (?, ?, ?, 'agi', 'Melee')",
        (hero_id, f"npc_dota_hero_{name}", name),
    )


def _seed_role_score(conn, hero_id: int, primary_pos: int) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO hero_role_scores "
        "(hero_id, pos1, pos2, pos3, pos4, pos5, flex_score, primary_pos) "
        "VALUES (?, 3, 3, 3, 3, 3, 5, ?)",
        (hero_id, primary_pos),
    )


def _seed_match(conn, match_id: int, duration: int) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO matches (id, start_time, duration, radiant_win) "
        "VALUES (?, 1700000000, ?, 1)",
        (match_id, duration),
    )


def _seed_mp(
    conn,
    match_id: int,
    slot: int,
    hero_id: int,
    win: bool,
    kills: int = 5,
    gpm: int = 500,
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO match_players "
        "(match_id, player_slot, hero_id, kills, deaths, assists, gpm, xpm, win) "
        "VALUES (?, ?, ?, ?, 2, 8, ?, 600, ?)",
        (match_id, slot, hero_id, kills, gpm, int(win)),
    )


# ── get_hero_phase_stats ──────────────────────────────────────────────────────

def test_phase_stats_empty_for_unknown_hero(db) -> None:
    with UnitOfWork() as uow:
        result = MatchTimelineRepository(uow.conn).get_hero_phase_stats(hero_id=9999)
    assert result == []


def test_phase_stats_early_game(db) -> None:
    """Матчі ≤ 1800s → phase='early'."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_match(uow.conn, 1, duration=1200)   # 20 хв — early
        _seed_match(uow.conn, 2, duration=1800)   # 30 хв — early (межа)
        _seed_mp(uow.conn, 1, 0, hero_id=1, win=True)
        _seed_mp(uow.conn, 2, 0, hero_id=1, win=False)

    with UnitOfWork() as uow:
        result = MatchTimelineRepository(uow.conn).get_hero_phase_stats(hero_id=1)

    assert len(result) == 1
    assert result[0].phase == "early"
    assert result[0].matches_played == 2
    assert result[0].wins == 1
    assert result[0].winrate == 0.5


def test_phase_stats_all_three_phases(db) -> None:
    """Матчі в усіх трьох фазах → 3 записи в порядку early→mid→late."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_match(uow.conn, 1, duration=1500)   # early
        _seed_match(uow.conn, 2, duration=2400)   # mid
        _seed_match(uow.conn, 3, duration=3600)   # late
        for match_id in range(1, 4):
            _seed_mp(uow.conn, match_id, 0, hero_id=1, win=True)

    with UnitOfWork() as uow:
        result = MatchTimelineRepository(uow.conn).get_hero_phase_stats(hero_id=1)

    assert len(result) == 3
    assert [r.phase for r in result] == ["early", "mid", "late"]
    for r in result:
        assert r.matches_played == 1
        assert r.winrate == 1.0


def test_phase_stats_mid_boundary(db) -> None:
    """duration=3000 → 'mid'; duration=3001 → 'late'."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_match(uow.conn, 1, duration=3000)   # межа mid
        _seed_match(uow.conn, 2, duration=3001)   # late
        _seed_mp(uow.conn, 1, 0, hero_id=1, win=True)
        _seed_mp(uow.conn, 2, 0, hero_id=1, win=True)

    with UnitOfWork() as uow:
        result = MatchTimelineRepository(uow.conn).get_hero_phase_stats(hero_id=1)

    phases = {r.phase for r in result}
    assert "mid" in phases
    assert "late" in phases
    assert "early" not in phases


def test_phase_stats_missing_phases_not_returned(db) -> None:
    """Якщо немає матчів в якійсь фазі — вона не повертається."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        # тільки late матчі
        _seed_match(uow.conn, 1, duration=4000)
        _seed_match(uow.conn, 2, duration=5000)
        _seed_mp(uow.conn, 1, 0, hero_id=1, win=True)
        _seed_mp(uow.conn, 2, 0, hero_id=1, win=False)

    with UnitOfWork() as uow:
        result = MatchTimelineRepository(uow.conn).get_hero_phase_stats(hero_id=1)

    assert len(result) == 1
    assert result[0].phase == "late"
    assert result[0].matches_played == 2


def test_phase_stats_avg_gpm_per_phase(db) -> None:
    """avg_gpm обчислюється окремо для кожної фази."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_match(uow.conn, 1, duration=1500)  # early
        _seed_match(uow.conn, 2, duration=4000)  # late
        _seed_mp(uow.conn, 1, 0, hero_id=1, win=True, gpm=300)
        _seed_mp(uow.conn, 2, 0, hero_id=1, win=True, gpm=700)

    with UnitOfWork() as uow:
        result = MatchTimelineRepository(uow.conn).get_hero_phase_stats(hero_id=1)

    by_phase = {r.phase: r for r in result}
    assert by_phase["early"].avg_gpm == 300.0
    assert by_phase["late"].avg_gpm == 700.0


def test_phase_stats_isolated_by_hero(db) -> None:
    """Статистика одного героя не впливає на іншого."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_hero(uow.conn, 2, "Axe")
        _seed_match(uow.conn, 1, duration=1500)
        _seed_mp(uow.conn, 1, 0, hero_id=1, win=True)
        _seed_mp(uow.conn, 1, 1, hero_id=2, win=False)

    with UnitOfWork() as uow:
        am = MatchTimelineRepository(uow.conn).get_hero_phase_stats(hero_id=1)
        axe = MatchTimelineRepository(uow.conn).get_hero_phase_stats(hero_id=2)

    assert am[0].wins == 1
    assert axe[0].wins == 0


# ── get_meta_snapshot ─────────────────────────────────────────────────────────

def test_meta_snapshot_empty_for_no_matches(db) -> None:
    with UnitOfWork() as uow:
        result = MatchTimelineRepository(uow.conn).get_meta_snapshot()
    assert result == []


def test_meta_snapshot_sorted_by_meta_score_desc(db) -> None:
    """meta_score = winrate * pickrate * 100, відсортовано DESC."""
    with UnitOfWork() as uow:
        # Anti-Mage carry: 8/10 = 0.8 wr, 10/15 pickrate
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_role_score(uow.conn, hero_id=1, primary_pos=1)
        # Axe offlane: 4/10 = 0.4 wr, 10/15 pickrate
        _seed_hero(uow.conn, 2, "Axe")
        _seed_role_score(uow.conn, hero_id=2, primary_pos=3)

        # 15 матчів: AM у 10, Axe у 10 (5 спільних)
        for i in range(1, 16):
            _seed_match(uow.conn, i, duration=2400)

        for i in range(1, 11):
            _seed_mp(uow.conn, i, 0, hero_id=1, win=(i <= 8))  # AM: 8 wins

        for i in range(6, 16):
            _seed_mp(uow.conn, i, 1, hero_id=2, win=(i <= 9))  # Axe: 4 wins

    with UnitOfWork() as uow:
        result = MatchTimelineRepository(uow.conn).get_meta_snapshot()

    assert len(result) == 2
    assert result[0].hero_id == 1   # AM: вищий winrate → вищий meta_score
    assert result[0].meta_score >= result[1].meta_score


def test_meta_snapshot_meta_score_calculation(db) -> None:
    """meta_score = round(winrate * pickrate * 100, 2)."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_role_score(uow.conn, hero_id=1, primary_pos=1)

        # 4 матчі, AM у всіх 4, 3 wins → winrate=0.75, pickrate=4/4=1.0
        for i in range(1, 5):
            _seed_match(uow.conn, i, duration=2400)
            _seed_mp(uow.conn, i, 0, hero_id=1, win=(i <= 3))

    with UnitOfWork() as uow:
        result = MatchTimelineRepository(uow.conn).get_meta_snapshot()

    assert len(result) == 1
    r = result[0]
    assert r.winrate == 0.75
    assert r.pickrate == 1.0
    assert r.meta_score == round(0.75 * 1.0 * 100, 2)


def test_meta_snapshot_filter_by_pos(db) -> None:
    """primary_pos фільтрує тільки героїв цієї позиції."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_role_score(uow.conn, hero_id=1, primary_pos=1)   # carry
        _seed_hero(uow.conn, 2, "Axe")
        _seed_role_score(uow.conn, hero_id=2, primary_pos=3)   # offlane

        for i in range(1, 6):
            _seed_match(uow.conn, i, duration=2400)
            _seed_mp(uow.conn, i, 0, hero_id=1, win=True)
            _seed_mp(uow.conn, i, 1, hero_id=2, win=True)

    with UnitOfWork() as uow:
        carry = MatchTimelineRepository(uow.conn).get_meta_snapshot(primary_pos=1)
        offlane = MatchTimelineRepository(uow.conn).get_meta_snapshot(primary_pos=3)
        all_pos = MatchTimelineRepository(uow.conn).get_meta_snapshot()

    assert len(carry) == 1 and carry[0].hero_id == 1
    assert len(offlane) == 1 and offlane[0].hero_id == 2
    assert len(all_pos) == 2


def test_meta_snapshot_limit(db) -> None:
    """limit обрізає результат."""
    with UnitOfWork() as uow:
        for hero_id in range(1, 6):
            _seed_hero(uow.conn, hero_id, f"hero_{hero_id}")
            _seed_role_score(uow.conn, hero_id=hero_id, primary_pos=1)
            for match_id in range(hero_id * 10, hero_id * 10 + 5):
                _seed_match(uow.conn, match_id, duration=2400)
                _seed_mp(uow.conn, match_id, 0, hero_id=hero_id, win=True)

    with UnitOfWork() as uow:
        result = MatchTimelineRepository(uow.conn).get_meta_snapshot(limit=3)

    assert len(result) == 3


def test_meta_snapshot_heroes_without_role_scores_excluded(db) -> None:
    """Герої без hero_role_scores не потрапляють в snapshot."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")          # без role scores
        _seed_hero(uow.conn, 2, "Axe")
        _seed_role_score(uow.conn, hero_id=2, primary_pos=3)

        for i in range(1, 4):
            _seed_match(uow.conn, i, duration=2400)
            _seed_mp(uow.conn, i, 0, hero_id=1, win=True)
            _seed_mp(uow.conn, i, 1, hero_id=2, win=True)

    with UnitOfWork() as uow:
        result = MatchTimelineRepository(uow.conn).get_meta_snapshot()

    assert len(result) == 1
    assert result[0].hero_id == 2   # тільки Axe (є role_scores)


def test_meta_snapshot_invalid_pos_raises(db) -> None:
    """primary_pos поза 1–5 → ValueError."""
    with UnitOfWork() as uow:
        with pytest.raises(ValueError, match="primary_pos must be 1-5"):
            MatchTimelineRepository(uow.conn).get_meta_snapshot(primary_pos=6)