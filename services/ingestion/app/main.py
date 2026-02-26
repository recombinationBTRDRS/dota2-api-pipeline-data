#services/ingestion/app/main.py
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from services.ingestion.app.config import settings
from services.ingestion.db.sqlite import init_db


def setup_logging() -> None: 
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logging.getLogger(__name__).info("Starting Ingestion Service")
    await asyncio.get_event_loop().run_in_executor(None, init_db)
    yield
    logging.getLogger(__name__).info("Shutting down Ingestion Service")



app = FastAPI(title="Ingestion Service", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok"}