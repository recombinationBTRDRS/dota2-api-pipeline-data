# services/ingestion/domains/matches/parsers.py
from services.ingestion.domains.matches.dtos import Match


def parse_match(contract: dict) -> Match:
    """Перетворює normalized contract dict → Domain Match.

    Використовує Match.model_validate для єдиної точки валідації:
    будь-які відсутні або некоректні поля (включно з вкладеними players)
    кидають pydantic.ValidationError — fail-fast без KeyError-сюрпризів.

    Args:
        contract: нормалізований dict від adapt_match().

    Returns:
        Провалідований Match DTO.

    Raises:
        pydantic.ValidationError: якщо contract не відповідає схемі.
    """
    return Match.model_validate(contract)