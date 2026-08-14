# Valuation Methodologies — Landscape Reference

Built for an agent-first equity research / valuation tool on SEC EDGAR. Organized by approach family, with a build-relevant cut on data requirements at the end. Methods you already listed are marked ✓.

---

## 1. Intrinsic / Absolute — discount future cash flows

The "what is it worth on its own fundamentals" family: forecast cash flows, discount to present value. Variants differ by *which* cash flow and *whose* claim.

- **FCFF / Enterprise DCF** ✓ (your "DCF") — discount unlevered free cash flow at WACC → enterprise value, less net debt → equity. The workhorse for most companies.
- **FCFE DCF** — discount levered free cash flow (post-debt) at cost of equity → equity value directly. Better when leverage is stable and central to the story (e.g. banks).
- **Dividend Discount Model (DDM)** ✓ — discount expected dividends at cost of equity. For mature, dividend-paying firms (utilities, some financials). Sub-variants:
  - Gordon Growth (single-stage, constant growth)
  - Two-stage / three-stage / H-model (growth that fades over time)
- **Residual Income Model (RIM)** ✓ — equity value = current book value + PV of future residual income (earnings above the equity charge). Strong when dividends/FCF are erratic but book value is meaningful. Firm-level analog: **Economic Value Added (EVA) / Economic Profit**.
- **Adjusted Present Value (APV)** — value the unlevered firm, then add PV of financing effects (tax shields, distress costs) separately. Best for changing capital structures — LBOs, project finance.
- **Capital Cash Flow (CCF)** — discount cash flows *including* the interest tax shield at the unlevered cost of capital; an alternative bookkeeping of the same economics as APV/WACC.

Structural choices that cut across all of the above:
- **Terminal value** — Gordon perpetuity vs. exit-multiple.
- **Discount rate** — WACC for the firm; CAPM or a build-up method for cost of equity.
- Probabilistic overlays — **scenario / sensitivity DCF** and **Monte Carlo DCF** (a distribution of values, not a point estimate).

---

## 2. Relative / Multiples — price against peers or the market

Apply a peer or market multiple to a fundamental metric. Split into equity (price) multiples and enterprise (capital-structure-neutral) multiples.

**Equity / price multiples**
- **P/E** ✓ (trailing & forward); **PEG** = P/E ÷ growth
- **P/B** ✓ (price-to-book) — common for financials
- **P/S** ✓ (price-to-sales) — for unprofitable / early-stage firms
- **P/CF, P/FCF** (cash-flow based)
- **Dividend yield** / payout-based
- **Price / NAV** — funds, REITs, holding companies

**Enterprise multiples** (neutralize leverage)
- **EV/EBITDA** ✓ — the most-used cross-company multiple
- **EV/EBIT** — when depreciation intensity differs across peers
- **EV/Sales (EV/Revenue)** — pre-profit companies
- **EV/FCF**, **EV/Invested Capital**, **EV/EBITDAR** (lease-heavy businesses)

**Sector-specific / KPI multiples** (when accounting earnings mislead)
- SaaS: **EV/ARR**, **EV/Revenue gated by Rule of 40**, LTV/CAC framing
- Internet / telecom: **EV per subscriber / MAU / DAU**
- Energy: **EV per BOE of reserves**, **EV/EBITDAX**
- Real estate: **cap rate**, **price per sq ft**
- Asset managers: **price / AUM**; marketplaces: **EV/GMV**, **EV/Bookings**
- Industrials / utilities: **EV per ton**, **EV per MW**

Two methodologies inside this family: **comparable companies (trading comps)** vs. **precedent transactions** (M&A deal multiples — these embed a control premium, so they run higher).

---

## 3. Asset-based / cost approach ✓ (your "asset-based valuation")

Value from the balance sheet rather than earnings — for asset-heavy, holding, distressed, or liquidating businesses.

- **Book value / tangible book value** of equity
- **Net Asset Value (NAV)** — mark assets and liabilities to fair value (REITs, funds, holding cos, natural resources)
- **Liquidation value** (orderly vs. forced) — a valuation floor
- **Replacement / reproduction cost**
- **Sum-of-the-Parts (SOTP)** — value each segment by its own appropriate method, then aggregate; for conglomerates. A meta-method that wraps the others.

---

## 4. Contingent-claim / option-based

Apply option pricing (Black-Scholes, binomial) where there's flexibility or an option-like payoff.

- **Real options** — option to expand, abandon, delay, or switch; for R&D, natural resources, strategic flexibility, early-stage
- **Equity as a call option on firm assets (Merton model)** — distressed or highly levered firms
- Option valuation of **patents, reserves, biotech pipelines**

---

## 5. Earnings-power, hybrid & private / early-stage

- **Earnings Power Value (EPV)** — Greenwald: normalized sustainable earnings ÷ cost of capital, no growth; triangulated against asset value
- **Capitalization of earnings** — cap rate on normalized earnings; standard in private/SMB valuation
- **Excess earnings method** — separates tangible-asset return from intangible value (private co / intangibles)
- **Graham number / Graham formulas** — classic intrinsic-value heuristics
- Startup-specific: **VC method** (exit value × target multiple, discounted at a high required return; pre/post-money), **First Chicago** (probability-weighted scenarios), and pre-revenue heuristics — **Berkus, Scorecard, Risk-factor summation**
- **LBO analysis** — not a valuation per se, but solves for the price that hits a target IRR; PE's implied "floor"

---

## 6. Market-derived — the market's own answer

- **Market capitalization** (price × shares) and **enterprise value** as observed
- **Analyst consensus / target prices**, 52-week trading range, implied value from the latest financing round (private)

---

## What's computable from EDGAR — the build-relevant cut

EDGAR gives you the **financial statements and XBRL-tagged data**, but *not* market prices. That splits the methods cleanly:

- **From filings alone:** book / tangible book, NAV inputs, residual-income and EPV inputs, historical FCFF/FCFE, and every *denominator* for multiples (EPS, EBITDA, sales, book value, FCF). Plus some sector KPIs disclosed in filings (subscribers, ARR sometimes, energy reserves in supplementary schedules).
- **Needs a market-data feed (prices):** every actual *multiple* (P/E, EV/EBITDA, etc. — you need price and EV), dividend yield, market cap. Pair EDGAR with a price source.
- **Needs forecasts / assumptions (the agent or user supplies):** all DCF / DDM / RIM going forward — growth, margins, WACC / cost of equity, terminal value. This is where your auditability edge lives: every assumption explicit and traceable.
- **Needs deal data:** precedent transactions (an M&A multiples database).
- **Extraction challenges:** sector KPIs aren't standardized across filings; segment data for SOTP is inconsistent company to company.

---

## How practitioners actually use these

No one picks a single method. Standard practice is to **triangulate** — run several (typically a DCF, a set of trading comps, sometimes precedent transactions and an asset floor) and present a **valuation range** ("football field"), then reason about *why* the methods diverge.

For an agent-first tool, that's the showcase: run multiple methods in parallel, surface the range, and make every input behind each one inspectable and explainable — the thing no chatbot-in-a-sidebar can do.
