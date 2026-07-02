"""Pydantic schemas shared by the API and the DCF engine."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class DcfInputs(BaseModel):
    """Everything the FCFF engine needs. All rates are decimals (0.08 = 8%)."""

    ticker: str = ""

    # Base-year financials
    base_revenue: float = Field(gt=0)
    base_margin: float = Field(gt=-1, lt=1, description="Current operating margin")
    target_margin: float = Field(gt=-1, lt=1, description="Margin reached by year 5")
    tax_rate: float = Field(ge=0, lt=1)
    sales_to_capital: float = Field(gt=0)

    # Growth
    growth_stage1: float = Field(gt=-0.5, lt=1, description="Revenue growth, years 1-5")
    terminal_growth: float = Field(ge=-0.05, lt=0.10)

    # Discount rate: either the components or a direct override
    risk_free: float | None = Field(default=None, ge=0, lt=0.25)
    beta: float | None = Field(default=None, gt=-1, lt=5)
    erp: float = Field(default=0.05, gt=0, lt=0.20, description="Equity risk premium")
    pretax_cost_of_debt: float | None = Field(default=None, ge=0, lt=0.30)
    wacc_override: float | None = Field(default=None, gt=0, lt=0.50)

    # Balance sheet / market
    market_cap: float | None = Field(default=None, gt=0)
    total_debt: float = Field(ge=0)
    cash: float = Field(ge=0)
    diluted_shares: float = Field(gt=0)
    current_price: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def check_consistency(self) -> "DcfInputs":
        if self.wacc_override is None:
            missing = [
                name
                for name in ("risk_free", "beta", "pretax_cost_of_debt", "market_cap")
                if getattr(self, name) is None
            ]
            if missing:
                raise ValueError(
                    f"Provide wacc_override or the WACC components; missing: {', '.join(missing)}"
                )
        if self.risk_free is not None and self.terminal_growth > self.risk_free:
            raise ValueError(
                f"Terminal growth ({self.terminal_growth:.2%}) cannot exceed the "
                f"risk-free rate ({self.risk_free:.2%})"
            )
        return self


class YearRow(BaseModel):
    year: int
    revenue: float
    growth: float
    margin: float
    ebit: float
    nopat: float
    reinvestment: float
    fcff: float
    pv: float


class SensitivityGrid(BaseModel):
    wacc_values: list[float]
    growth_values: list[float]
    # matrix[i][j] = intrinsic value per share at wacc_values[i], growth_values[j];
    # None where wacc <= growth makes the terminal value undefined
    matrix: list[list[float | None]]


class DcfResult(BaseModel):
    years: list[YearRow]
    wacc: float
    cost_of_equity: float | None
    sum_pv_explicit: float
    terminal_value: float
    pv_terminal: float
    enterprise_value: float
    equity_value: float
    intrinsic_per_share: float
    upside: float | None = None
    sensitivity: SensitivityGrid
    warnings: list[str] = []


class FiscalYearData(BaseModel):
    """One fiscal year of normalized fundamentals. None = not reported/extractable."""

    fiscal_year: int
    end_date: str
    revenue: float | None = None
    operating_income: float | None = None
    depreciation_amortization: float | None = None
    capex: float | None = None
    working_capital: float | None = None
    pretax_income: float | None = None
    tax_expense: float | None = None
    total_debt: float | None = None
    cash: float | None = None
    diluted_shares: float | None = None


class DerivedMetrics(BaseModel):
    """History-derived anchors used to pre-fill assumption inputs."""

    latest_revenue: float | None = None
    latest_operating_margin: float | None = None
    avg_operating_margin_5y: float | None = None
    revenue_cagr_1y: float | None = None
    revenue_cagr_5y: float | None = None
    revenue_cagr_10y: float | None = None
    effective_tax_rate: float | None = None
    sales_to_capital_5y: float | None = None
    latest_total_debt: float | None = None
    latest_cash: float | None = None
    latest_diluted_shares: float | None = None


class CompanyPayload(BaseModel):
    ticker: str
    cik: str
    company_name: str
    sic: str | None = None
    sic_description: str | None = None
    is_financial: bool = False
    years: list[FiscalYearData]
    derived: DerivedMetrics
    warnings: list[str] = []


class MarketData(BaseModel):
    ticker: str
    price: float | None = None
    beta: float | None = None
    market_cap: float | None = None
    risk_free: float | None = None
    warnings: list[str] = []


class SavedValuation(BaseModel):
    id: int | None = None
    ticker: str
    company_name: str
    created_at: datetime | None = None
    price_at_run: float | None = None
    inputs: DcfInputs
    result: DcfResult
