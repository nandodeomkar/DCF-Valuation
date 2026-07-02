from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import companies, market, valuations

app = FastAPI(title="DCF Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(companies.router)
app.include_router(market.router)
app.include_router(valuations.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
