# DCF Dashboard

A personal, locally-run web dashboard for valuing US public companies with a
driver-based FCFF discounted cash flow model.

Type a ticker → the app fetches ~10 years of fundamentals from SEC EDGAR plus
the live price, beta, and 10Y Treasury yield → you set forecast assumptions
(each shown beside its historical anchor) → it computes intrinsic value per
share with a sensitivity grid → save the run to revisit later.

**Core idea:** every assumption is explicit and traceable. Fetched facts and
your judgment are kept visually and structurally separate.

## Run it

```powershell
.\run.ps1        # Windows
./run.sh         # macOS / Linux / Git Bash
```

Then open **http://localhost:5173**. First run installs dependencies
(Python venv + npm).

## Architecture

```
backend/   FastAPI (Python 3.12)
  app/dcf/engine.py        Pure FCFF engine — no I/O, unit-tested against closed forms
  app/services/edgar.py    SEC EDGAR companyfacts/submissions fetch, disk cache (24h TTL)
  app/services/normalize.py XBRL tag fallback chains → clean per-fiscal-year history
  app/services/market_data.py  Price/beta (Yahoo), risk-free (FRED DGS10)
  app/routers/             /api/company, /api/market, /api/dcf, /api/valuations
  app/db.py                SQLite (backend/data/valuations.sqlite3)
frontend/  React + Vite + TypeScript
  pages/Home.tsx           Saved valuations vs. live prices
  pages/Company.tsx        History → assumptions → verdict (analyst narrative)
```

## The model

Ten-year, two-stage FCFF (Damodaran-style):

- Years 1–5: revenue grows at your stage-1 rate; operating margin fades
  linearly from the current margin to your target.
- Years 6–10: growth fades linearly to the terminal rate.
- Reinvestment = revenue change ÷ sales-to-capital ratio.
- WACC from CAPM build-up (rf + β·ERP, blended with after-tax cost of debt at
  market-value weights) or a direct override.
- Terminal value assumes stable growth with ROIC = WACC
  (reinvestment rate = g/WACC); requires g < WACC and g ≤ rf.
- Sensitivity: 5×5 grid over WACC ±1.5% × terminal growth ±1%.

## Tests

```
cd backend && .venv/Scripts/python.exe -m pytest
```

Engine tests verify against independent closed-form perpetuity/growing-annuity
math; normalization tests use synthetic EDGAR fixtures (tag switches, restated
comparatives, missing concepts, financial-sector flag).

## Data sources & caveats

- **Fundamentals:** SEC EDGAR XBRL (10-K annual data). Filers tag concepts
  inconsistently; missing values become manual inputs with a warning.
- **Price/beta:** Yahoo Finance (unofficial endpoints; can break).
- **Risk-free:** FRED 10Y Treasury (DGS10).
- Financial-sector companies (SIC 6000–6999) get a "FCFF DCF is unreliable
  for financials" warning.
- Personal tool. The assumptions — and the conclusions — are yours, not advice.

Design docs: [docs/superpowers/specs/](docs/superpowers/specs/) ·
[docs/superpowers/plans/](docs/superpowers/plans/)
