from services.ingestion.providers.opendota.client import OpenDotaClient, MatchProvider
from services.ingestion.providers.opendota.adapters import adapt_match
from services.ingestion.domains.matches.parsers import parse_match


def ingest_match(match_id: int, provider: MatchProvider | None = None):
    provider = provider or OpenDotaClient()
    raw = provider.get_match(match_id)
    contract = adapt_match(raw)
    match = parse_match(contract)
    return match