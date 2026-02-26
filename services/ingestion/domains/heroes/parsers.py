# services/ingestion/domains/heroes/parsers.py
from services.ingestion.domains.heroes.dtos import Hero


def parse_hero(raw: dict) -> Hero:
    """Парсить raw dict з OpenDota /heroes → Hero DTO.

    OpenDota повертає primary_attr як 'str'/'agi'/'int'/'all'
    і attack_type як 'Melee'/'Ranged' — передаємо напряму.

    Args:
        raw: один елемент з відповіді GET /heroes.

    Returns:
        Провалідований Hero DTO.

    Raises:
        ValidationError: якщо raw не відповідає схемі.
    """
    return Hero.model_validate(raw)


def parse_heroes(raw_list: list[dict]) -> list[Hero]:
    """Парсить список raw dict → list[Hero].

    Args:
        raw_list: відповідь GET /heroes (список героїв).

    Returns:
        Список провалідованих Hero DTO.
    """
    return [parse_hero(raw) for raw in raw_list]