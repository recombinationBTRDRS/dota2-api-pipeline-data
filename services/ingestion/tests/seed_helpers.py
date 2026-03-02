# services/ingestion/tests/seed_helpers.py
"""Спільні seed-хелпери для тестів pre-computed layer (Epic 5).

Імпортуються в test_computed_repository.py і test_computed_endpoints.py.
"""
import sqlite3


def seed_hero(conn: sqlite3.Connection, hero_id: int, name: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO heroes (id, name, localized_name, primary_attr, attack_type) "
        "VALUES (?, ?, ?, 'agi', 'Melee')",
        (hero_id, f"npc_dota_hero_{name}", name),
    )


def seed_role_score(conn: sqlite3.Connection, hero_id: int, primary_pos: int) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO hero_role_scores "
        "(hero_id, pos1, pos2, pos3, pos4, pos5, flex_score, primary_pos) "
        "VALUES (?, 3, 3, 3, 3, 3, 5, ?)",
        (hero_id, primary_pos),
    )


def seed_item(conn: sqlite3.Connection, item_id: int, name: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO items (id, name, localized_name, cost) VALUES (?, ?, ?, 0)",
        (item_id, f"item_{name}", name),
    )


def seed_match(
    conn: sqlite3.Connection,
    match_id: int,
    patch: int | None = None,
    region: int | None = None,
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO matches (id, start_time, duration, radiant_win, patch, region) "
        "VALUES (?, 1700000000, 2400, 1, ?, ?)",
        (match_id, patch, region),
    )


def seed_mp(
    conn: sqlite3.Connection,
    match_id: int,
    slot: int,
    hero_id: int,
    win: bool,
    gpm: int = 500,
    xpm: int = 600,
    kills: int = 5,
    deaths: int = 2,
    assists: int = 8,
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO match_players "
        "(match_id, player_slot, hero_id, kills, deaths, assists, gpm, xpm, win) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (match_id, slot, hero_id, kills, deaths, assists, gpm, xpm, int(win)),
    )


def seed_item_slot(
    conn: sqlite3.Connection,
    match_id: int,
    slot: int,
    item_id: int,
    item_slot: int = 0,
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO match_player_items (match_id, player_slot, slot, item_id) "
        "VALUES (?, ?, ?, ?)",
        (match_id, slot, item_slot, item_id),
    )