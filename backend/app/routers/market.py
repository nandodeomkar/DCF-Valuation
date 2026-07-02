from fastapi import APIRouter

from app.models import MarketData
from app.services import market_data

router = APIRouter(prefix="/api", tags=["market"])


@router.get("/market/{ticker}", response_model=MarketData)
def get_market(ticker: str) -> MarketData:
    return market_data.get_market_data(ticker)
