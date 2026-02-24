from fastapi import FastAPI

app = FastAPI(title="Ingestion Service")

@app.get("/health")
def health():
    return {"status": "ok"}