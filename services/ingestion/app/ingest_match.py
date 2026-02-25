# services/ingestion/app/ingest_match.py
import logging
from typing import Optional

from services.ingestion.app.persist import persist_match
from services.ingestion.domains.matches.dtos import Match
from services.ingestion.domains.matches.parsers import parse_match
from services.ingestion.providers.opendota.adapters import adapt_match
from services.ingestion.providers.opendota.client import MatchProvider, OpenDotaClient

logger = logging.getLogger(__name__)


def ingest_match(match_id: int, provider: Optional[MatchProvider] = None) -> Match:
    logger.info("Start ingest match_id=%s", match_id)
    
    try:
        client = provider if provider is not None else OpenDotaClient()

        raw = client.get_match(match_id)
        contract = adapt_match(raw)
        domain_match = parse_match(contract)
        persist_match(domain_match)

        logger.info("Ingest success match_id=%s", match_id)
        return domain_match

    except Exception:
        logger.exception("Ingest failed match_id=%s", match_id)
        raise