# services/analysis/app/main.py
import logging

from fastapi import FastAPI

from services.analysis.app.config import config
from services.analysis.db.sqlite import init_db, check_db

logging.basicConfig(
    level=getattr(logging, config.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Dota 2 — Match Analysis Service",
    version="0.1.0",
    description="Watchlist + Match Report: draft quality, economy, teamfight analysis.",
)


@app.on_event("startup")
async def startup() -> None:
    init_db()
    logger.info("Analysis service started. DB: %s", config.db_path)


@app.get("/health", tags=["system"])
def health() -> dict:
    db_ok = check_db()
    return {"status": "ok" if db_ok else "degraded", "db_ok": db_ok}
