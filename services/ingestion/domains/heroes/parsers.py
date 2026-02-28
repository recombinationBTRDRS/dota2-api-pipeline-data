# services/ingestion/domains/heroes/parsers.py

from services.ingestion.domains.heroes.dtos import Hero


def parse_hero(raw: dict) -> Hero:
    """Парсить raw dict з OpenDota /heroes → Hero DTO.

    Допускає неповні payload'и у тестах (primary_attr, attack_type можуть бути відсутні).
    Для таких випадків підставляються безпечні дефолти:
      - primary_attr = "all"
      - attack_type = "Melee"

    Це дозволяє використовувати fake providers без повної OpenDota-схеми.
    """
    if isinstance(raw, Hero):
        return raw

    raw = {
        "primary_attr": raw.get("primary_attr", "all"),
        "attack_type": raw.get("attack_type", "Melee"),
        **raw,
    }
    return Hero.model_validate(raw)


def parse_heroes(raw_list: list[dict]) -> list[Hero]:
    """Парсить список raw dict → list[Hero].

    Args:
        raw_list: відповідь GET /heroes (список героїв).

    Returns:
        Список провалідованих Hero DTO.
    """
    return [parse_hero(raw) for raw in raw_list]