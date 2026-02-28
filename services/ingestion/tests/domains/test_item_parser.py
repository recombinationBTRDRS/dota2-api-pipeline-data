# services/ingestion/tests/domains/test_item_parser.py
"""Unit-тести для parse_item і parse_items."""

from services.ingestion.domains.items.parsers import parse_item, parse_items


def test_parse_item_valid() -> None:
    """Валідний raw dict → Item DTO з коректними полями."""
    item = parse_item("blink", {"id": 1, "dname": "Blink Dagger", "cost": 2250,
                                 "secret_shop": 0, "side_shop": 0, "recipe": 0})
    assert item is not None
    assert item.id == 1
    assert item.name == "blink"
    assert item.localized_name == "Blink Dagger"
    assert item.cost == 2250
    assert item.secret_shop is False


def test_parse_item_secret_shop() -> None:
    """secret_shop=1 → bool True."""
    item = parse_item("eaglesong", {"id": 99, "dname": "Eaglesong", "cost": 3200,
                                     "secret_shop": 1, "side_shop": 0, "recipe": 0})
    assert item is not None
    assert item.secret_shop is True


def test_parse_item_recipe() -> None:
    """recipe=1 → bool True, cost може бути 0."""
    item = parse_item("recipe_blink", {"id": 200, "dname": "Recipe: Blink Dagger",
                                        "cost": 0, "secret_shop": 0, "side_shop": 0, "recipe": 1})
    assert item is not None
    assert item.recipe is True
    assert item.cost == 0


def test_parse_item_missing_id_returns_none() -> None:
    """Відсутній id → None (службовий запис)."""
    result = parse_item("some_constant", {"dname": "Something", "cost": 0})
    assert result is None


def test_parse_item_missing_dname_returns_none() -> None:
    """Відсутній dname → None."""
    result = parse_item("broken_item", {"id": 5, "cost": 100})
    assert result is None


def test_parse_item_none_cost_defaults_to_zero() -> None:
    """cost=None в API → 0 (деякі предмети не мають ціни)."""
    item = parse_item("tango", {"id": 10, "dname": "Tango", "cost": None})
    assert item is not None
    assert item.cost == 0


def test_parse_items_dict() -> None:
    """Повний dict → список Item, службові записи без id пропускаються."""
    raw = {
        "blink": {"id": 1, "dname": "Blink Dagger", "cost": 2250},
        "branches": {"id": 2, "dname": "Iron Branch", "cost": 50},
        "no_id_entry": {"dname": "Ghost", "cost": 0},   # пропустити
        "null_val": None,                                  # пропустити
    }
    items = parse_items(raw)
    assert len(items) == 2
    assert {i.name for i in items} == {"blink", "branches"}


def test_parse_items_empty() -> None:
    """Порожній dict → порожній список."""
    assert parse_items({}) == []