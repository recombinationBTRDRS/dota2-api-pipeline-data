#services/ingestion/app/main.py
from fastapi import FastAPI
from services.ingestion.db.sqlite import init_db
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    init_db()
    yield
    # shutdown (якщо треба — закриття конекшенів, клієнтів тощо)

app = FastAPI(title="Ingestion Service", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok"}