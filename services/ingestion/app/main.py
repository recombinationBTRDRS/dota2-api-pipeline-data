# services/ingestion/app/main.py
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from services.ingestion.app.config import settings
from services.ingestion.app.state import app_state
from services.ingestion.db.sqlite import get_connection, init_db

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Налаштовує structured logging з рівнем з settings."""
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _check_db() -> bool:
    """Перевіряє доступність БД через SELECT 1. Повертає True якщо OK."""
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
        return True
    except Exception:
        logger.exception("DB health check failed")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler: ініціалізація при старті, cleanup при зупинці."""
    setup_logging()
    logger.info("Starting Ingestion Service")
    await asyncio.get_event_loop().run_in_executor(None, init_db)
    yield
    logger.info("Shutting down Ingestion Service")


app = FastAPI(title="Ingestion Service", lifespan=lifespan)


@app.get("/health")
def health() -> JSONResponse:
    """Health check endpoint.

    Перевіряє доступність БД через SELECT 1.
    Повертає 200 якщо все OK, 503 якщо БД недоступна.

    Returns:
        JSON з полями status і db_ok.
    """
    db_ok = _check_db()
    status_code = 200 if db_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if db_ok else "degraded",
            "db_ok": db_ok,
        },
    )


@app.get("/stats")
def stats() -> JSONResponse:
    """Статистика останнього discovery циклу.

    Дані оновлюються runner-ом після кожного run_cycle().
    Якщо runner ще не запускався — повертає null поля.

    Returns:
        JSON з last_cycle_at (unix timestamp) і last_cycle_stats.
    """
    return JSONResponse(
        content={
            "last_cycle_at": app_state.last_cycle_at,
            "last_cycle_stats": app_state.last_cycle_stats,
        }
    )