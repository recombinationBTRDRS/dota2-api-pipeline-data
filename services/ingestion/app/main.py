# services/ingestion/app/main.py
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from services.ingestion.app.config import settings
from services.ingestion.app.routers.analytics import router as analytics_router
from services.ingestion.app.routers.computed import router as computed_router
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
    logger.info("Starting Dota 2 Analytics API v1.0.0")
    await asyncio.get_event_loop().run_in_executor(None, init_db)
    yield
    logger.info("Shutting down Dota 2 Analytics API")


app = FastAPI(
    title="Dota 2 Analytics API",
    version="1.0.0",
    description=(
        "Аналітична платформа для Dota 2. "
        "Збирає матчі з OpenDota API, будує pre-computed статистику "
        "по героях, білдах, counter-picks і synergy.\n\n"
        "**Analytics API** (`/heroes`, `/analytics`) — raw queries по матчах.\n"
        "**Computed API** (`/computed`) — pre-computed таблиці (швидше, для Frontend)."
    ),
    lifespan=lifespan,
)

# CORS — дозволяємо Frontend (Vite :5173) звертатись до API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(analytics_router, tags=["analytics"])
app.include_router(computed_router, tags=["computed"])


@app.get("/health", tags=["system"])
def health() -> JSONResponse:
    """Перевірка стану сервісу і DB з'єднання."""
    db_ok = _check_db()
    return JSONResponse(
        status_code=200 if db_ok else 503,
        content={"status": "ok" if db_ok else "degraded", "db_ok": db_ok},
    )


@app.get("/stats", tags=["system"])
def stats() -> JSONResponse:
    """Стан останнього discovery циклу (in-memory)."""
    return JSONResponse(
        content={
            "last_cycle_at": app_state.last_cycle_at,
            "last_cycle_stats": app_state.last_cycle_stats,
        }
    )