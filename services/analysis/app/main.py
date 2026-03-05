# services/analysis/app/main.py
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from services.analysis.app.config import config
from services.analysis.app.routers.reports import router as reports_router
from services.analysis.app.routers.watchlist import router as watchlist_router
from services.analysis.db.sqlite import check_db, init_db

logging.basicConfig(
    level=getattr(logging, config.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    logger.info("Analysis service started. DB: %s", config.db_path)
    yield


app = FastAPI(
    title="Dota 2 — Match Analysis Service",
    version="0.1.0",
    description="Watchlist + Match Report: draft quality, economy, teamfight analysis.",
    lifespan=lifespan,
)

app.include_router(watchlist_router)
app.include_router(reports_router)

@app.get("/health", tags=["system"])
def health() -> dict:
    db_ok = check_db()
    return {"status": "ok" if db_ok else "degraded", "db_ok": db_ok}