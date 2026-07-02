"""Pure FCFF DCF engine. No I/O — takes DcfInputs, returns DcfResult.

Model: 10-year, two-stage with fade (Damodaran-style).
- Years 1-5: revenue grows at growth_stage1; operating margin fades linearly
  from base_margin to target_margin.
- Years 6-10: margin holds at target_margin; growth fades linearly from
  growth_stage1 to terminal_growth (reaching it exactly in year 10).
- Reinvestment in explicit years = revenue change / sales_to_capital.
- Terminal value assumes stable growth with ROIC = WACC, so the terminal
  reinvestment rate is terminal_growth / WACC.
"""

from __future__ import annotations

from app.models import DcfInputs, DcfResult, SensitivityGrid, YearRow

FORECAST_YEARS = 10
STAGE1_YEARS = 5

WACC_SENSITIVITY_STEPS = [-0.015, -0.0075, 0.0, 0.0075, 0.015]
GROWTH_SENSITIVITY_STEPS = [-0.01, -0.005, 0.0, 0.005, 0.01]


class DcfError(ValueError):
    """Raised when inputs pass schema validation but the model is not computable."""


def compute_wacc(inputs: DcfInputs) -> tuple[float, float | None]:
    """Return (wacc, cost_of_equity). cost_of_equity is None when overridden."""
    if inputs.wacc_override is not None:
        return inputs.wacc_override, None
    cost_of_equity = inputs.risk_free + inputs.beta * inputs.erp
    after_tax_cod = inputs.pretax_cost_of_debt * (1 - inputs.tax_rate)
    equity = inputs.market_cap
    debt = inputs.total_debt
    total = equity + debt
    wacc = cost_of_equity * equity / total + after_tax_cod * debt / total
    return wacc, cost_of_equity


def _growth_for_year(year: int, g1: float, g_term: float) -> float:
    if year <= STAGE1_YEARS:
        return g1
    # Years 6-10: linear fade, hitting g_term exactly at year 10
    step = (g_term - g1) / (FORECAST_YEARS - STAGE1_YEARS)
    return g1 + step * (year - STAGE1_YEARS)


def _margin_for_year(year: int, base: float, target: float) -> float:
    if year >= STAGE1_YEARS:
        return target
    # Years 1-4: linear fade from base toward target (year 5 = target)
    step = (target - base) / STAGE1_YEARS
    return base + step * year


def _project(inputs: DcfInputs, wacc: float, g_term: float) -> tuple[list[YearRow], float, float]:
    """Project explicit years and terminal value at the given wacc / terminal growth.

    Returns (year_rows, terminal_value, enterprise_value).
    """
    if wacc <= g_term:
        raise DcfError(
            f"WACC ({wacc:.2%}) must exceed terminal growth ({g_term:.2%}) "
            "or the terminal value is undefined"
        )

    rows: list[YearRow] = []
    revenue = inputs.base_revenue
    sum_pv = 0.0
    nopat = 0.0
    for year in range(1, FORECAST_YEARS + 1):
        growth = _growth_for_year(year, inputs.growth_stage1, g_term)
        margin = _margin_for_year(year, inputs.base_margin, inputs.target_margin)
        prev_revenue = revenue
        revenue = prev_revenue * (1 + growth)
        ebit = revenue * margin
        nopat = ebit * (1 - inputs.tax_rate)
        reinvestment = (revenue - prev_revenue) / inputs.sales_to_capital
        fcff = nopat - reinvestment
        pv = fcff / (1 + wacc) ** year
        sum_pv += pv
        rows.append(
            YearRow(
                year=year,
                revenue=revenue,
                growth=growth,
                margin=margin,
                ebit=ebit,
                nopat=nopat,
                reinvestment=reinvestment,
                fcff=fcff,
                pv=pv,
            )
        )

    # Terminal: stable growth, reinvestment rate = g / WACC (ROIC = WACC)
    terminal_nopat = nopat * (1 + g_term)
    terminal_reinvestment_rate = g_term / wacc if g_term > 0 else 0.0
    terminal_fcff = terminal_nopat * (1 - terminal_reinvestment_rate)
    terminal_value = terminal_fcff / (wacc - g_term)
    pv_terminal = terminal_value / (1 + wacc) ** FORECAST_YEARS

    return rows, terminal_value, sum_pv + pv_terminal


def _per_share(inputs: DcfInputs, enterprise_value: float) -> float:
    equity = enterprise_value - inputs.total_debt + inputs.cash
    return equity / inputs.diluted_shares


def _sensitivity(inputs: DcfInputs, base_wacc: float) -> SensitivityGrid:
    wacc_values = [round(base_wacc + step, 6) for step in WACC_SENSITIVITY_STEPS]
    growth_values = [round(inputs.terminal_growth + step, 6) for step in GROWTH_SENSITIVITY_STEPS]
    matrix: list[list[float | None]] = []
    for wacc in wacc_values:
        row: list[float | None] = []
        for g in growth_values:
            if wacc <= g or wacc <= 0:
                row.append(None)
                continue
            try:
                _, _, ev = _project(inputs, wacc, g)
                row.append(_per_share(inputs, ev))
            except DcfError:
                row.append(None)
        matrix.append(row)
    return SensitivityGrid(wacc_values=wacc_values, growth_values=growth_values, matrix=matrix)


def run_dcf(inputs: DcfInputs) -> DcfResult:
    wacc, cost_of_equity = compute_wacc(inputs)
    rows, terminal_value, enterprise_value = _project(inputs, wacc, inputs.terminal_growth)

    pv_terminal = terminal_value / (1 + wacc) ** FORECAST_YEARS
    sum_pv_explicit = enterprise_value - pv_terminal
    equity_value = enterprise_value - inputs.total_debt + inputs.cash
    intrinsic = equity_value / inputs.diluted_shares

    warnings: list[str] = []
    if equity_value < 0:
        warnings.append("Equity value is negative: debt exceeds enterprise value.")
    if any(r.fcff < 0 for r in rows):
        warnings.append(
            "FCFF is negative in some forecast years (reinvestment exceeds NOPAT); "
            "check growth and sales-to-capital assumptions."
        )
    if pv_terminal / enterprise_value > 0.85 and enterprise_value > 0:
        warnings.append(
            f"Terminal value is {pv_terminal / enterprise_value:.0%} of enterprise value; "
            "the valuation rests almost entirely on terminal assumptions."
        )

    upside = None
    if inputs.current_price:
        upside = intrinsic / inputs.current_price - 1

    return DcfResult(
        years=rows,
        wacc=wacc,
        cost_of_equity=cost_of_equity,
        sum_pv_explicit=sum_pv_explicit,
        terminal_value=terminal_value,
        pv_terminal=pv_terminal,
        enterprise_value=enterprise_value,
        equity_value=equity_value,
        intrinsic_per_share=intrinsic,
        upside=upside,
        sensitivity=_sensitivity(inputs, wacc),
        warnings=warnings,
    )
