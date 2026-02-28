# services/ingestion/app/main.py
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from services.ingestion.app.config import settings
from services.ingestion.app.routers.analytics import router as analytics_router
from services.ingestion.app.state import app_state
from services.ingestion.db.sqlite import get_connection, init_db

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _check_db() -> bool:
    conn = get_connection()
    try:
        conn.execute("SELECT 1")
        return True
    except Exception:
        logger.exception("DB health check failed")
        return False
    finally:
        conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Starting Ingestion Service")
    await asyncio.get_event_loop().run_in_executor(None, init_db)
    yield
    logger.info("Shutting down Ingestion Service")


app = FastAPI(title="Ingestion Service", lifespan=lifespan)

app.include_router(analytics_router, tags=["analytics"])


@app.get("/health")
def health() -> JSONResponse:
    db_ok = _check_db()
    return JSONResponse(
        status_code=200 if db_ok else 503,
        content={"status": "ok" if db_ok else "degraded", "db_ok": db_ok},
    )


@app.get("/stats")
def stats() -> JSONResponse:
    return JSONResponse(
        content={
            "last_cycle_at": app_state.last_cycle_at,
            "last_cycle_stats": app_state.last_cycle_stats,
        }
    )