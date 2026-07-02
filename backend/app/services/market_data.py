"""Market data: current price, beta, market cap (yfinance) and the 10Y Treasury
yield as risk-free rate (FRED). Every source failure degrades to None plus a
warning — a dead feed must never block running a DCF.
"""

from __future__ import annotations

import csv
import io

import httpx

from app.models import MarketData

FRED_DGS10_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"
STOOQ_QUOTE_URL = "https://stooq.com/q/l/?s={symbol}.us&f=sd2t2ohlcv&h&e=csv"


def get_market_data(ticker: str) -> MarketData:
    warnings: list[str] = []
    price = beta = market_cap = None

    try:
        import yfinance as yf

        t = yf.Ticker(ticker)
        info = t.fast_info
        price = _positive(getattr(info, "last_price", None))
        market_cap = _positive(getattr(info, "market_cap", None))
        try:
            beta = t.info.get("beta")
        except Exception:
            beta = None
    except Exception as exc:
        warnings.append(f"yfinance lookup failed: {exc}")

    if price is None:
        price = _stooq_price(ticker)
        if price is None:
            warnings.append("Could not fetch a live price; enter it manually.")

    if beta is None:
        warnings.append("Beta unavailable; defaulting is up to you (1.0 = market average).")

    risk_free = _fred_dgs10()
    if risk_free is None:
        warnings.append("Could not fetch the 10Y Treasury yield; enter the risk-free rate manually.")

    return MarketData(
        ticker=ticker.upper(),
        price=price,
        beta=beta,
        market_cap=market_cap,
        risk_free=risk_free,
        warnings=warnings,
    )


def _positive(value) -> float | None:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _stooq_price(ticker: str) -> float | None:
    try:
        response = httpx.get(STOOQ_QUOTE_URL.format(symbol=ticker.lower()), timeout=15)
        response.raise_for_status()
        rows = list(csv.DictReader(io.StringIO(response.text)))
        return _positive(rows[0]["Close"]) if rows else None
    except Exception:
        return None


def _fred_dgs10() -> float | None:
    try:
        response = httpx.get(FRED_DGS10_URL, timeout=15, follow_redirects=True)
        response.raise_for_status()
        rows = list(csv.reader(io.StringIO(response.text)))
        for row in reversed(rows):
            if len(row) == 2 and row[1] not in (".", "", "DGS10"):
                return float(row[1]) / 100.0
    except Exception:
        return None
    return None
