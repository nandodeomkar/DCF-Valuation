# DCF Dashboard — Implementation Plan

Spec: [2026-07-02-dcf-dashboard-design.md](../specs/2026-07-02-dcf-dashboard-design.md)

Build order goes core-outward: pure engine first (testable without network), then data services, then API, then frontend. Each phase ends with a commit and a working state.

## Phase 1 — Backend skeleton + DCF engine

1. Scaffold `backend/`: venv, `requirements.txt` (fastapi, uvicorn, edgartools, yfinance, httpx, pydantic, pytest), package layout from spec.
2. `models.py`: `DcfInputs`, `DcfResult`, `YearRow`, `SavedValuation` Pydantic schemas with validation (`WACC > g_term`, `g_term ≤ rf`, rate bounds).
3. `dcf/engine.py`: `run_dcf(inputs) -> DcfResult` per spec formulas — 10yr, margin fade years 1–5, growth fade years 6–10, terminal value with stable-growth reinvestment, WACC build-up or override, EV→equity bridge, 5×5 sensitivity grid.
4. Tests: hand-computed reference case (documented in test file), edge cases (zero growth, negative FCFF, g_term near WACC, full-fade boundaries).

**Done when:** `pytest` green on engine.

## Phase 2 — Data services

5. `services/edgar.py`: ticker→CIK map (SEC ticker file, cached), company facts fetch via edgartools, disk cache in `backend/data/cache/` with 24h TTL and force-refresh flag. SEC-compliant User-Agent.
6. `services/normalize.py`: XBRL concept fallback chains → 10yr annual series (revenue, EBIT, D&A, capex, ΔWC, effective tax, debt, cash, diluted shares) + derived metrics (margins, CAGRs, sales-to-capital). Gaps allowed.
7. `services/market_data.py`: price + beta via yfinance, Stooq price fallback, 10Y Treasury via FRED CSV endpoint (no API key). Each source failure → `None` + warning string, never an exception outward.
8. Tests: normalize against captured AAPL fixture + one messy filer fixture.

**Done when:** real fetch for AAPL returns sane series; tests green.

## Phase 3 — API + persistence

9. `db.py`: SQLite table `valuations` (id, ticker, name, created_at, inputs JSON, result JSON, price_at_run).
10. Routers: `GET /api/company/{ticker}` (fundamentals + derived + warnings), `GET /api/market/{ticker}` (price, beta, rf), `POST /api/dcf`, `GET/POST/DELETE /api/valuations`.
11. Financial-sector warning via SIC code in company payload.
12. `TestClient` smoke tests with mocked services.

**Done when:** curl walk-through of all endpoints works.

## Phase 4 — Frontend

13. Scaffold `frontend/` with Vite + React + TypeScript. Typed API client mirroring Pydantic schemas.
14. Home page: saved valuations table (with live current price), ticker search → company page.
15. Company page, analyst-narrative layout:
    - Section 1: fundamentals table + revenue/margin chart (recharts).
    - Section 2: assumption inputs with historical anchors, history-derived defaults, warnings for missing data → manual fields.
    - Section 3: verdict card (intrinsic vs price, upside %), FCFF projection table, EV→equity bridge, sensitivity grid heatmap, save button.
16. Loading/error states for every fetch; warning banners (feed down, financial-sector).

**Done when:** full flow works in browser against live backend.

## Phase 5 — Polish + ship

17. `run.ps1` / `run.sh`: start uvicorn (8000) + Vite (5173) together.
18. README: setup, run, architecture summary.
19. Manual E2E pass: AAPL (clean), a messy filer, a bank (warning), a junk ticker (error path). Fix what breaks.
20. Final commit.
