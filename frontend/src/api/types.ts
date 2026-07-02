// Mirrors backend/app/models.py Pydantic schemas.

export interface FiscalYearData {
  fiscal_year: number;
  end_date: string;
  revenue: number | null;
  operating_income: number | null;
  depreciation_amortization: number | null;
  capex: number | null;
  working_capital: number | null;
  pretax_income: number | null;
  tax_expense: number | null;
  total_debt: number | null;
  cash: number | null;
  diluted_shares: number | null;
}

export interface DerivedMetrics {
  latest_revenue: number | null;
  latest_operating_margin: number | null;
  avg_operating_margin_5y: number | null;
  revenue_cagr_1y: number | null;
  revenue_cagr_5y: number | null;
  revenue_cagr_10y: number | null;
  effective_tax_rate: number | null;
  sales_to_capital_5y: number | null;
  latest_total_debt: number | null;
  latest_cash: number | null;
  latest_diluted_shares: number | null;
}

export interface CompanyPayload {
  ticker: string;
  cik: string;
  company_name: string;
  sic: string | null;
  sic_description: string | null;
  is_financial: boolean;
  years: FiscalYearData[];
  derived: DerivedMetrics;
  warnings: string[];
}

export interface MarketData {
  ticker: string;
  price: number | null;
  beta: number | null;
  market_cap: number | null;
  risk_free: number | null;
  warnings: string[];
}

export interface DcfInputs {
  ticker: string;
  base_revenue: number;
  base_margin: number;
  target_margin: number;
  tax_rate: number;
  sales_to_capital: number;
  growth_stage1: number;
  terminal_growth: number;
  risk_free: number | null;
  beta: number | null;
  erp: number;
  pretax_cost_of_debt: number | null;
  wacc_override: number | null;
  market_cap: number | null;
  total_debt: number;
  cash: number;
  diluted_shares: number;
  current_price: number | null;
}

export interface YearRow {
  year: number;
  revenue: number;
  growth: number;
  margin: number;
  ebit: number;
  nopat: number;
  reinvestment: number;
  fcff: number;
  pv: number;
}

export interface SensitivityGrid {
  wacc_values: number[];
  growth_values: number[];
  matrix: (number | null)[][];
}

export interface DcfResult {
  years: YearRow[];
  wacc: number;
  cost_of_equity: number | null;
  sum_pv_explicit: number;
  terminal_value: number;
  pv_terminal: number;
  enterprise_value: number;
  equity_value: number;
  intrinsic_per_share: number;
  upside: number | null;
  sensitivity: SensitivityGrid;
  warnings: string[];
}

export interface SavedValuation {
  id: number | null;
  ticker: string;
  company_name: string;
  created_at: string | null;
  price_at_run: number | null;
  inputs: DcfInputs;
  result: DcfResult;
}
