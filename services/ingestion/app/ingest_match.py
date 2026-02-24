# services/ingestion/app/ingest_match.py
from services.ingestion.providers.opendota.client import OpenDotaClient
from services.ingestion.providers.opendota.adapters import adapt_match
from services.ingestion.domains.matches.parsers import parse_match


def ingest_match(match_id: int):
    client = OpenDotaClient()
    raw = client.get_match(match_id)
    contract = adapt_match(raw)
    domain_match = parse_match(contract)
    return domain_match