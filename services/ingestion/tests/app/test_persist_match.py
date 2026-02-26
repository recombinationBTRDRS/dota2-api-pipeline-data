# services/ingestion/tests/app/test_persist_match.py
"""Unit-тести для app-шару: перевіряємо що ingest_match викликає persist_match.

persist_match мокується в модулі ingest_match (де він використовується).
Інтеграційні тести (реальний SQLite) — у tests/integration/test_persist_integration.py.
"""
from unittest.mock import MagicMock, patch

from services.ingestion.domains.matches.dtos import Match


def make_fake_raw(match_id: int = 1) -> dict:
    """Фіксований raw dict що імітує відповідь OpenDota API."""
    return {
        "match_id": match_id,
        "duration": 222,
        "radiant_win": True,
        "start_time": 111,
        "radiant_score": 30,
        "dire_score": 20,
        "players": [
            {
                "account_id": 123,
                "hero_id": 1,
                "kills": 10,
                "deaths": 2,
                "assists": 5,
                "gpm": 600,
                "xpm": 700,
                "isRadiant": True,
                "win": 1,
            }
        ],
    }


class FakeProvider:
    """Stub провайдера — повертає фіксований raw dict без HTTP."""

    def get_match(self, match_id: int) -> dict:
        return make_fake_raw(match_id)


# Патчимо там де функція ВИКОРИСТОВУЄТЬСЯ, а не де визначена.
# ingest_match.py робить: from services.ingestion.app.persist import persist_match
# тому patch має бути на services.ingestion.app.ingest_match.persist_match
@patch("services.ingestion.app.ingest_match.persist_match")
def test_ingest_match_calls_persist_with_correct_match(mock_persist: MagicMock) -> None:
    """ingest_match викликає persist_match з правильним Match об'єктом."""
    from services.ingestion.app.ingest_match import ingest_match

    ingest_match(match_id=1, provider=FakeProvider())

    mock_persist.assert_called_once()
    called_match = mock_persist.call_args.args[0]
    assert isinstance(called_match, Match)
    assert called_match.id == 1
    assert called_match.radiant_win is True
    assert len(called_match.players) == 1
    assert called_match.players[0].account_id == 123


@patch("services.ingestion.app.ingest_match.persist_match")
def test_ingest_match_returns_match_dto(mock_persist: MagicMock) -> None:
    """ingest_match повертає Match DTO після успішного pipeline."""
    from services.ingestion.app.ingest_match import ingest_match

    result = ingest_match(match_id=1, provider=FakeProvider())

    assert isinstance(result, Match)
    assert result.id == 1
    mock_persist.assert_called_once()