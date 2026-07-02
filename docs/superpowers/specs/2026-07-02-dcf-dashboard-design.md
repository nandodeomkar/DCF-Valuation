# DCF Valuation Dashboard — Design

**Date:** 2026-07-02
**Status:** Approved (pending spec review)

## Purpose

A personal, locally-run web dashboard for valuing US public companies with a discounted cash flow model. The user enters a ticker; the app fetches everything knowable (fundamentals from SEC EDGAR, market price, risk-free rate), the user supplies forecast assumptions anchored against fetched history, and the app computes an intrinsic value per share with a sensitivity analysis. Valuations are saved locally for later review.

Core design value, inherited from the parent valuation project: **every assumption explicit and traceable.** Fetched data and user judgment are visually and structurally separate.

## Decisions Made

| Question | Decision |
|---|---|
| Market scope | US stocks (SEC EDGAR fundamentals) |
| Deployment | Local app — backend and frontend run on the user's machine |
| Model depth | Driver-based FCFF, Damodaran-style, 10-year 2-stage with fade |
| Data fetching | Maximum: EDGAR fundamentals, live price, beta, 10Y Treasury yield |
| Persistence | Valuations saved locally (SQLite); no watchlist in v1 |
| Stack | FastAPI (Python) backend + React (Vite + TypeScript) frontend |
| Company page layout | "Analyst narrative" — vertical flow: history → assumptions → verdict |

## Architecture

```
dcf-dashboard/
├── backend/                    # FastAPI (Python)
│   ├── app/
│   │   ├── main.py             # FastAPI app, CORS, routes
│   │   ├── routers/
│   │   │   ├── companies.py    # GET /api/company/{ticker} — fundamentals
│   │   │   ├── market.py       # GET /api/market/{ticker} — price, beta, risk-free rate
│   │   │   └── valuations.py   # POST /api/dcf (run), CRUD /api/valuations (saved)
│   │   ├── services/
│   │   │   ├── edgar.py        # EDGAR XBRL fetch via edgartools, ~10yr history, disk cache
│   │   │   ├── market_data.py  # price + beta (yfinance, Stooq fallback), 10Y Treasury (FRED)
│   │   │   └── normalize.py    # raw XBRL → clean driver history
│   │   ├── dcf/
│   │   │   └── engine.py       # pure-Python FCFF engine — no I/O
│   │   ├── models.py           # Pydantic schemas: DcfInputs, DcfResult, SavedValuation
│   │   └── db.py               # SQLite — saved valuations
│   └── requirements.txt
├── frontend/                   # React + Vite + TypeScript
│   └── src/
│       ├── pages/              # Home (saved valuations + search), Company (main flow)
│       ├── components/         # AssumptionInput, FundamentalsTable, SensitivityGrid, ValuationChart
│       └── api/                # typed client for backend
└── README.md
```

Key principles:

- **The DCF engine is a pure module with zero I/O.** `run_dcf(DcfInputs) -> DcfResult`. Unit-testable against hand-computed cases; UI and data layers are replaceable around it.
- **SQLite file in the project directory** for saved valuations. No server database.
- **Disk cache for EDGAR responses** (~24h TTL plus a manual refresh button). Price fetched fresh on each load.
- **One-command startup**: a script launches uvicorn (port 8000) and Vite dev server (port 5173).

## UI

**Home page:** list of saved valuations (company, date, intrinsic value, price at time of run, and current price — fetched live when the page loads) plus a ticker search box.

**Company page — "Analyst narrative" layout**, a vertical scroll in three sections mirroring how an analyst reasons:

1. **What EDGAR says** — 10-year fundamentals table and revenue/margin charts. Pure fetched data.
2. **Your assumptions** — each input (growth, margin, tax rate, WACC components, terminal growth, sales-to-capital) rendered beside its historical anchor (e.g. revenue growth input next to 1/5/10-year CAGRs). Pre-filled with history-derived defaults.
3. **Verdict** — intrinsic value per share vs. market price with upside/downside %, per-year FCFF projection table, EV→equity bridge, and sensitivity grid. Save button persists the full run.

## Data Flow

1. Ticker entered → `GET /api/company/{ticker}`.
2. `edgar.py`: ticker → CIK, fetch XBRL company facts via `edgartools`; disk cache.
3. `normalize.py` → ~10-year annual series: revenue, operating income, D&A, capex, change in working capital, effective tax rate, total debt, cash, diluted shares. Derived: operating margin, revenue CAGR (1/5/10yr), sales-to-capital ratio.
4. `market_data.py`: current price and beta via yfinance (Stooq fallback for price); 10Y Treasury yield via FRED.
5. Frontend renders history (section 1); assumptions (section 2) pre-filled from history.
6. `POST /api/dcf` with `DcfInputs` → engine → `DcfResult` renders (section 3).
7. Save → SQLite row: ticker, date, full `DcfInputs`, full `DcfResult`, price at time of run.

## DCF Engine Specification

Ten-year, two-stage FCFF model with linear fade:

- **Years 1–5:** revenue growth `g1`; operating margin fades linearly from current to user's target margin.
- **Years 6–10:** growth fades linearly from `g1` to terminal growth `g_term`.
- `EBIT_t = Revenue_t × margin_t`
- `NOPAT_t = EBIT_t × (1 − tax_rate)`
- `Reinvestment_t = ΔRevenue_t / sales_to_capital`
- `FCFF_t = NOPAT_t − Reinvestment_t`
- **WACC:** `cost_of_equity = rf + β × ERP` (ERP default 5.0%, editable); blended with after-tax cost of debt at market-value weights. Direct WACC override supported. Constant across years in v1.
- **Terminal value:** `TV = FCFF_11 / (WACC − g_term)` where terminal reinvestment rate = `g_term / WACC` (stable-growth assumption: ROIC = WACC). Validation: `g_term ≤ rf`.
- `EV = Σ PV(FCFF_t) + PV(TV)`; `Equity = EV − total_debt + cash`; intrinsic per share = `Equity / diluted_shares`.
- **Sensitivity:** 5×5 grid, WACC ±1.5% × terminal growth ±1%.

**Output (`DcfResult`):** per-year table (revenue, EBIT, FCFF, PV), EV→equity bridge, intrinsic value per share, upside % vs. price, sensitivity matrix.

## Error Handling

- Unknown ticker / no EDGAR data → clear UI message; nothing crashes.
- Inconsistent XBRL tagging → `normalize.py` tries fallback tag chains per concept (e.g. `Revenues` → `RevenueFromContractWithCustomerExcludingAssessedTax` → `SalesRevenueNet`). Missing years render as gaps. Engine minimum inputs: revenue, EBIT, shares, debt, cash — any missing value becomes a manual input field with a warning.
- Price or FRED feed unavailable → warning banner; price and risk-free rate become manual inputs. A data-layer failure never blocks running the DCF.
- Engine input validation via Pydantic: `WACC > g_term` enforced, sane bounds on all rates → HTTP 422 with a human-readable message.
- Financial-sector companies (banks, insurers, by SIC code) → warning banner that FCFF DCF is unreliable for financials; run not blocked.

## Testing

- **Engine:** pytest against a hand-computed, spreadsheet-verified reference case, plus edge cases — zero growth, negative-FCFF years, `g_term` near WACC, margin fade boundaries.
- **Normalize:** fixture JSONs captured from real EDGAR responses (AAPL plus one messy filer); assert extracted series.
- **API:** FastAPI `TestClient` smoke tests with services mocked.
- **Frontend:** TypeScript strict mode and build check; manual end-to-end pass at the end.

## Out of Scope (v1)

- Other valuation methods (comps, DDM, residual income) — the parent project's landscape doc covers the roadmap; this tool is DCF only.
- Watchlist / portfolio views.
- Non-US listings.
- Three-statement modeling, Monte Carlo, scenario weighting.
- Deployment/hosting, authentication, multi-user anything.
