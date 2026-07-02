"""Turn raw SEC companyfacts JSON into a clean per-fiscal-year driver history.

Filers tag the same economic concept differently (and switch tags over time),
so every concept has an ordered fallback chain and values are merged per year:
for each fiscal year, the first tag in the chain that reported a value wins.

Annual values are identified as 10-K facts with a ~1-year duration (duration
concepts) or a fiscal-year-end instant (instant concepts). The same period
appears in several filings (comparatives), so the latest-filed value wins.
"""

from __future__ import annotations

from app.models import CompanyPayload, DerivedMetrics, FiscalYearData

MAX_YEARS = 11  # 10 usable years + one prior year for deltas

REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
]
OPERATING_INCOME_TAGS = ["OperatingIncomeLoss"]
DA_TAGS = [
    "DepreciationDepletionAndAmortization",
    "DepreciationAmortizationAndAccretionNet",
    "Depreciation",
]
CAPEX_TAGS = [
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsToAcquireProductiveAssets",
    "PaymentsForCapitalImprovements",
]
PRETAX_INCOME_TAGS = [
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
]
TAX_TAGS = ["IncomeTaxExpenseBenefit"]
LTD_NONCURRENT_TAGS = ["LongTermDebtNoncurrent"]
LTD_CURRENT_TAGS = ["LongTermDebtCurrent"]
TOTAL_DEBT_TAGS = ["LongTermDebt", "DebtLongtermAndShorttermCombinedAmount"]
CASH_TAGS = [
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
]
ASSETS_CURRENT_TAGS = ["AssetsCurrent"]
LIABILITIES_CURRENT_TAGS = ["LiabilitiesCurrent"]
DILUTED_SHARES_TAGS = [
    "WeightedAverageNumberOfDilutedSharesOutstanding",
    "WeightedAverageNumberOfSharesOutstandingBasic",
]

MIN_DURATION_DAYS = 330
MAX_DURATION_DAYS = 395


def _annual_series(facts: dict, tags: list[str], unit: str, instant: bool) -> dict[str, float]:
    """Merge tag chain into {fiscal-year-end-date: value}, first tag per year wins."""
    merged: dict[str, float] = {}
    gaap = facts.get("facts", {}).get("us-gaap", {})
    for tag in tags:
        entries = gaap.get(tag, {}).get("units", {}).get(unit, [])
        best: dict[str, tuple[str, float]] = {}  # end -> (filed, val)
        for entry in entries:
            if entry.get("form") != "10-K" or entry.get("val") is None:
                continue
            end = entry.get("end")
            if not end:
                continue
            if instant:
                if entry.get("start"):
                    continue
            else:
                start = entry.get("start")
                if not start:
                    continue
                duration = _days_between(start, end)
                if not (MIN_DURATION_DAYS <= duration <= MAX_DURATION_DAYS):
                    continue
            filed = entry.get("filed", "")
            if end not in best or filed > best[end][0]:
                best[end] = (filed, float(entry["val"]))
        for end, (_, val) in best.items():
            merged.setdefault(end, val)
    return merged


def _days_between(start: str, end: str) -> int:
    from datetime import date

    y1, m1, d1 = map(int, start.split("-"))
    y2, m2, d2 = map(int, end.split("-"))
    return (date(y2, m2, d2) - date(y1, m1, d1)).days


def _cagr(newer: float | None, older: float | None, years: int) -> float | None:
    if newer is None or older is None or older <= 0 or newer <= 0:
        return None
    return (newer / older) ** (1 / years) - 1


def normalize(ticker: str, cik: str, facts: dict, submissions: dict) -> CompanyPayload:
    warnings: list[str] = []

    revenue = _annual_series(facts, REVENUE_TAGS, "USD", instant=False)
    op_income = _annual_series(facts, OPERATING_INCOME_TAGS, "USD", instant=False)
    da = _annual_series(facts, DA_TAGS, "USD", instant=False)
    capex = _annual_series(facts, CAPEX_TAGS, "USD", instant=False)
    pretax = _annual_series(facts, PRETAX_INCOME_TAGS, "USD", instant=False)
    tax = _annual_series(facts, TAX_TAGS, "USD", instant=False)
    shares = _annual_series(facts, DILUTED_SHARES_TAGS, "shares", instant=False)
    ltd_noncurrent = _annual_series(facts, LTD_NONCURRENT_TAGS, "USD", instant=True)
    ltd_current = _annual_series(facts, LTD_CURRENT_TAGS, "USD", instant=True)
    total_debt_direct = _annual_series(facts, TOTAL_DEBT_TAGS, "USD", instant=True)
    cash = _annual_series(facts, CASH_TAGS, "USD", instant=True)
    assets_current = _annual_series(facts, ASSETS_CURRENT_TAGS, "USD", instant=True)
    liabilities_current = _annual_series(facts, LIABILITIES_CURRENT_TAGS, "USD", instant=True)

    if not revenue:
        warnings.append("No annual revenue found in EDGAR filings; enter revenue manually.")

    # Fiscal-year timeline comes from revenue; fall back to operating income
    end_dates = sorted(revenue.keys() or op_income.keys())[-MAX_YEARS:]

    years: list[FiscalYearData] = []
    for end in end_dates:
        debt = None
        if end in ltd_noncurrent:
            debt = ltd_noncurrent[end] + ltd_current.get(end, 0.0)
        elif end in total_debt_direct:
            debt = total_debt_direct[end]

        wc = None
        if end in assets_current and end in liabilities_current:
            wc = assets_current[end] - liabilities_current[end]

        years.append(
            FiscalYearData(
                fiscal_year=int(end[:4]),
                end_date=end,
                revenue=revenue.get(end),
                operating_income=op_income.get(end),
                depreciation_amortization=da.get(end),
                capex=capex.get(end),
                working_capital=wc,
                pretax_income=pretax.get(end),
                tax_expense=tax.get(end),
                total_debt=debt,
                cash=cash.get(end),
                diluted_shares=shares.get(end),
            )
        )

    derived = _derive(years, warnings)

    sic = str(submissions.get("sic") or "") or None
    sic_description = submissions.get("sicDescription") or None
    is_financial = bool(sic and sic.isdigit() and 6000 <= int(sic) <= 6999)
    if is_financial:
        warnings.append(
            "This is a financial-sector company; an FCFF DCF is unreliable for "
            "banks and insurers (debt is raw material, not financing)."
        )

    return CompanyPayload(
        ticker=ticker.upper(),
        cik=cik,
        company_name=facts.get("entityName") or submissions.get("name") or ticker.upper(),
        sic=sic,
        sic_description=sic_description,
        is_financial=is_financial,
        years=years,
        derived=derived,
        warnings=warnings,
    )


def _derive(years: list[FiscalYearData], warnings: list[str]) -> DerivedMetrics:
    if not years:
        return DerivedMetrics()

    latest = years[-1]
    by_offset = {len(years) - 1 - i: y for i, y in enumerate(years)}  # 0 = latest

    margin = None
    if latest.revenue and latest.operating_income is not None:
        margin = latest.operating_income / latest.revenue

    margins_5y = [
        y.operating_income / y.revenue
        for y in years[-5:]
        if y.revenue and y.operating_income is not None
    ]
    avg_margin_5y = sum(margins_5y) / len(margins_5y) if margins_5y else None

    def rev(offset: int) -> float | None:
        y = by_offset.get(offset)
        return y.revenue if y else None

    effective_tax = None
    if latest.tax_expense is not None and latest.pretax_income and latest.pretax_income > 0:
        effective_tax = min(max(latest.tax_expense / latest.pretax_income, 0.0), 0.6)

    # Sales-to-capital over the last <=5 year-over-year steps:
    # reinvestment = capex - D&A + change in working capital
    delta_rev_sum = 0.0
    reinvest_sum = 0.0
    for prev, curr in zip(years[-6:], years[-6:][1:]):
        parts = (
            curr.revenue,
            prev.revenue,
            curr.capex,
            curr.depreciation_amortization,
            curr.working_capital,
            prev.working_capital,
        )
        if any(p is None for p in parts):
            continue
        delta_rev_sum += curr.revenue - prev.revenue
        reinvest_sum += curr.capex - curr.depreciation_amortization + (
            curr.working_capital - prev.working_capital
        )
    sales_to_capital = None
    if reinvest_sum > 0 and delta_rev_sum > 0:
        sales_to_capital = delta_rev_sum / reinvest_sum

    missing_core = [
        name
        for name, value in (
            ("revenue", latest.revenue),
            ("operating income", latest.operating_income),
            ("total debt", latest.total_debt),
            ("cash", latest.cash),
            ("diluted shares", latest.diluted_shares),
        )
        if value is None
    ]
    if missing_core:
        warnings.append(
            f"Missing from latest filing: {', '.join(missing_core)}. "
            "Fill these in manually before running the DCF."
        )

    return DerivedMetrics(
        latest_revenue=latest.revenue,
        latest_operating_margin=margin,
        avg_operating_margin_5y=avg_margin_5y,
        revenue_cagr_1y=_cagr(rev(0), rev(1), 1),
        revenue_cagr_5y=_cagr(rev(0), rev(5), 5),
        revenue_cagr_10y=_cagr(rev(0), rev(10), 10),
        effective_tax_rate=effective_tax,
        sales_to_capital_5y=sales_to_capital,
        latest_total_debt=latest.total_debt,
        latest_cash=latest.cash,
        latest_diluted_shares=latest.diluted_shares,
    )
