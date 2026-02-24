import json
from pathlib import Path
from services.ingestion.app.parser import parse_match


def test_parse_match():
    path = Path(__file__).parent / "fixtures" / "opendota_match.json"
    raw = json.loads(path.read_text(encoding="utf-8"))

    match = parse_match(raw)

    assert match.match_id == 7654321098
    assert match.radiant_win is True
    assert len(match.players) == 1

    player = match.players[0]
    assert player.hero_id == 83
    assert player.kills == 10
    assert player.items[0] == 50