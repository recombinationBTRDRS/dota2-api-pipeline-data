# services/ingestion/domains/items/parsers.py
"""Парсер відповіді OpenDota /constants/items.

OpenDota повертає об'єкт де ключ — internal name, значення — dict з полями:
    id, dname, cost, secret_shop, side_shop, recipe, ...

Приклад:
    {
      "blink": {"id": 1, "dname": "Blink Dagger", "cost": 2250, ...},
      "blades_of_attack": {"id": 2, "dname": "Blades of Attack", "cost": 450, ...}
    }
"""
from services.ingestion.domains.items.dtos import Item


def parse_item(name: str, raw: dict) -> Item | None:
    """Парсить один предмет з відповіді /constants/items.

    Пропускає записи без id або dname — деякі константи не є справжніми
    предметами (наприклад службові записи без id).

    Args:
        name: internal key ('blink').
        raw: dict з полями id, dname, cost тощо.

    Returns:
        Item DTO або None якщо запис не є валідним предметом.
    """
    item_id = raw.get("id")
    dname = raw.get("dname")

    if not isinstance(item_id, int) or not dname:
        return None

    return Item(
        id=item_id,
        name=name,
        localized_name=dname,
        cost=raw.get("cost") or 0,
        secret_shop=bool(raw.get("secret_shop", False)),
        side_shop=bool(raw.get("side_shop", False)),
        recipe=bool(raw.get("recipe", False)),
    )


def parse_items(raw_dict: dict) -> list[Item]:
    """Парсить весь dict з /constants/items → list[Item].

    Пропускає записи без id/dname без падіння.

    Args:
        raw_dict: повна відповідь GET /constants/items.

    Returns:
        Список валідних Item DTO.
    """
    items = []
    for name, data in raw_dict.items():
        if not isinstance(data, dict):
            continue
        item = parse_item(name, data)
        if item is not None:
            items.append(item)
    return items