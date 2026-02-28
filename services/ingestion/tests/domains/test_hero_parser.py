# services/ingestion/tests/domains/test_hero_parser.py
"""Unit-тести для parse_hero і parse_heroes."""
import pytest
from pydantic import ValidationError

from services.ingestion.domains.heroes.parsers import parse_hero, parse_heroes

VALID_RAW = {
    "id": 1,
    "name": "npc_dota_hero_antimage",
    "localized_name": "Anti-Mage",
    "primary_attr": "agi",
    "attack_type": "Melee",
}


def test_parse_hero_valid() -> None:
    """Валідний raw dict → Hero DTO з коректними полями."""
    hero = parse_hero(VALID_RAW)
    assert hero.id == 1
    assert hero.name == "npc_dota_hero_antimage"
    assert hero.localized_name == "Anti-Mage"
    assert hero.primary_attr == "agi"
    assert hero.attack_type == "Melee"


def test_parse_hero_universal_attr() -> None:
    """primary_attr='all' (universal heroes) — валідний."""
    raw = {**VALID_RAW, "id": 138, "primary_attr": "all"}
    hero = parse_hero(raw)
    assert hero.primary_attr == "all"


def test_parse_hero_ranged() -> None:
    """attack_type='Ranged' — валідний."""
    raw = {**VALID_RAW, "attack_type": "Ranged"}
    hero = parse_hero(raw)
    assert hero.attack_type == "Ranged"


def test_parse_hero_invalid_attr() -> None:
    """Невалідний primary_attr → ValidationError."""
    raw = {**VALID_RAW, "primary_attr": "unknown"}
    with pytest.raises(ValidationError):
        parse_hero(raw)


def test_parse_hero_missing_field() -> None:
    """Відсутнє обов'язкове поле → ValidationError."""
    raw = {k: v for k, v in VALID_RAW.items() if k != "localized_name"}
    with pytest.raises(ValidationError):
        parse_hero(raw)


def test_parse_heroes_list() -> None:
    """Список raw dict → список Hero DTO."""
    raw_list = [
        VALID_RAW,
        {**VALID_RAW, "id": 2, "name": "npc_dota_hero_axe", "localized_name": "Axe",
         "primary_attr": "str", "attack_type": "Melee"},
    ]
    heroes = parse_heroes(raw_list)
    assert len(heroes) == 2
    assert heroes[0].id == 1
    assert heroes[1].id == 2


def test_parse_heroes_empty_list() -> None:
    """Порожній список → порожній результат."""
    assert parse_heroes([]) == []