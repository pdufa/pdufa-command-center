"""Launch with: uvicorn main:app --host 0.0.0.0 --port 8000.

Deploy on a Python-capable backend; Next.js uses the server-side client below.
"""
from fastapi import FastAPI
from alpaca_api import router as alpaca_router

app = FastAPI(title="PDUFA Market Data API", version="0.1.0")
app.include_router(alpaca_router)


@app.get("/health")
def health():
    return {"status": "ok"}
