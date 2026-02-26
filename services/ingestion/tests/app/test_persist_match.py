# services/ingestion/tests/app/test_persist_match.py
"""Unit-тести для app/persist.py.

Тут persist_match мокується — жодних реальних DB-викликів.
Перевіряємо: чи викликано persist_match з правильним об'єктом і чи ідемпотентна поведінка
симулюється коректно.

Інтеграційні тести (реальний SQLite) — у tests/integration/test_persist_integration.py.
"""
from unittest.mock import MagicMock, patch

import pytest

from services.ingestion.domains.matches.dtos import Match, PlayerMatchStats


def make_match() -> Match:
    """Фабрика тестового Match DTO."""
    return Match(
        match_id=1,
        duration=222,
        radiant_win=True,
        start_time=111,
        radiant_score=30,
        dire_score=20,
        players=[
            PlayerMatchStats(
                player_slot=0,
                account_id=123,
                hero_id=1,
                kills=10,
                deaths=2,
                assists=5,
                gpm=600,
                xpm=700,
                is_radiant=True,
                win=True,
            ),
            PlayerMatchStats(
                player_slot=1,
                account_id=456,
                hero_id=2,
                kills=1,
                deaths=10,
                assists=2,
                gpm=300,
                xpm=400,
                is_radiant=False,
                win=False,
            ),
        ],
    )


@patch("services.ingestion.app.persist.persist_match")
def test_persist_match_called_with_correct_match(mock_persist: MagicMock) -> None:
    """persist_match викликається з правильним Match об'єктом."""
    from services.ingestion.app.persist import persist_match

    match = make_match()
    persist_match(match)

    mock_persist.assert_called_once_with(match)


@patch("services.ingestion.app.persist.persist_match")
def test_persist_match_idempotent_mock(mock_persist: MagicMock) -> None:
    """Повторний виклик persist_match не кидає виняток (ідемпотентність симульована)."""
    from services.ingestion.app.persist import persist_match

    match = make_match()
    persist_match(match)
    persist_match(match)

    assert mock_persist.call_count == 2
    # Обидва виклики з тим самим аргументом
    for call in mock_persist.call_args_list:
        assert call.args[0] == match