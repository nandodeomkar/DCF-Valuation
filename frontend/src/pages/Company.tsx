import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { ApiError, api } from "../api/client";
import type { CompanyPayload, DcfInputs, DcfResult, MarketData } from "../api/types";
import { Assumptions } from "../components/Assumptions";
import { Banners } from "../components/Banners";
import { Fundamentals } from "../components/Fundamentals";
import { Verdict } from "../components/Verdict";
import { price } from "../format";

const REQUIRED: { key: keyof DcfInputs; label: string }[] = [
  { key: "base_revenue", label: "base revenue" },
  { key: "base_margin", label: "base margin" },
  { key: "target_margin", label: "target margin" },
  { key: "tax_rate", label: "tax rate" },
  { key: "sales_to_capital", label: "sales-to-capital" },
  { key: "growth_stage1", label: "revenue growth" },
  { key: "terminal_growth", label: "terminal growth" },
  { key: "total_debt", label: "total debt" },
  { key: "cash", label: "cash" },
  { key: "diluted_shares", label: "diluted shares" },
];
const WACC_COMPONENTS: { key: keyof DcfInputs; label: string }[] = [
  { key: "risk_free", label: "risk-free rate" },
  { key: "beta", label: "beta" },
  { key: "pretax_cost_of_debt", label: "cost of debt" },
  { key: "market_cap", label: "market cap" },
];

function clamp(value: number, lo: number, hi: number): number {
  return Math.min(Math.max(value, lo), hi);
}

function buildDefaults(company: CompanyPayload, market: MarketData): Partial<DcfInputs> {
  const d = company.derived;
  const rf = market.risk_free;
  const growth = d.revenue_cagr_5y ?? d.revenue_cagr_10y ?? d.revenue_cagr_1y;
  const margin = d.latest_operating_margin;
  const target =
    margin != null && d.avg_operating_margin_5y != null
      ? Math.max(margin, d.avg_operating_margin_5y)
      : margin ?? d.avg_operating_margin_5y;
  return {
    ticker: company.ticker,
    base_revenue: d.latest_revenue ?? undefined,
    base_margin: margin ?? undefined,
    target_margin: target ?? undefined,
    tax_rate: d.effective_tax_rate != null ? clamp(d.effective_tax_rate, 0, 0.35) : 0.21,
    sales_to_capital: d.sales_to_capital_5y ?? 2.0,
    growth_stage1: growth != null ? clamp(growth, -0.05, 0.25) : undefined,
    terminal_growth: rf != null ? Math.min(0.025, rf) : 0.025,
    risk_free: rf,
    beta: market.beta ?? 1.0,
    erp: 0.05,
    pretax_cost_of_debt: rf != null ? rf + 0.012 : undefined,
    wacc_override: null,
    market_cap: market.market_cap,
    total_debt: d.latest_total_debt ?? undefined,
    cash: d.latest_cash ?? undefined,
    diluted_shares: d.latest_diluted_shares ?? undefined,
    current_price: market.price,
  };
}

export function Company() {
  const { ticker = "" } = useParams();
  const [company, setCompany] = useState<CompanyPayload | null>(null);
  const [market, setMarket] = useState<MarketData | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [inputs, setInputs] = useState<Partial<DcfInputs>>({});
  const [result, setResult] = useState<DcfResult | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savedId, setSavedId] = useState<number | null>(null);

  const load = useCallback(
    async (refresh: boolean) => {
      setLoading(true);
      setLoadError(null);
      setResult(null);
      setSavedId(null);
      try {
        const [companyData, marketData] = await Promise.all([
          api.company(ticker, refresh),
          api.market(ticker),
        ]);
        setCompany(companyData);
        setMarket(marketData);
        setInputs(buildDefaults(companyData, marketData));
      } catch (e) {
        setCompany(null);
        setLoadError(e instanceof ApiError ? e.message : `Could not reach the backend: ${e}`);
      } finally {
        setLoading(false);
      }
    },
    [ticker],
  );

  useEffect(() => {
    void load(false);
  }, [load]);

  const patch = (p: Partial<DcfInputs>) => {
    setInputs((prev) => ({ ...prev, ...p }));
    setSavedId(null);
  };

  const missing = REQUIRED.filter((f) => inputs[f.key] == null).map((f) => f.label);
  if (inputs.wacc_override == null) {
    missing.push(...WACC_COMPONENTS.filter((f) => inputs[f.key] == null).map((f) => f.label));
  }

  const run = async () => {
    setRunning(true);
    setRunError(null);
    setSavedId(null);
    try {
      setResult(await api.runDcf(inputs as DcfInputs));
    } catch (e) {
      setResult(null);
      setRunError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  const save = async () => {
    if (!company || !result) return;
    setSaving(true);
    try {
      const saved = await api.saveValuation({
        id: null,
        ticker: company.ticker,
        company_name: company.company_name,
        created_at: null,
        price_at_run: inputs.current_price ?? null,
        inputs: inputs as DcfInputs,
        result,
      });
      setSavedId(saved.id);
    } catch (e) {
      setRunError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="spinner">Fetching EDGAR filings and market data…</div>;
  if (loadError)
    return (
      <>
        <Banners warnings={[loadError]} kind="error" />
        <button className="ghost" onClick={() => void load(false)}>
          Retry
        </button>
      </>
    );
  if (!company) return null;

  return (
    <>
      <div className="card company-header">
        <div>
          <h1>
            {company.company_name} <span className="muted">({company.ticker})</span>
          </h1>
          <div className="muted">
            {company.sic_description ?? "—"} · CIK {company.cik}
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div className="price-tag">{price(market?.price)}</div>
          <div className="muted">10Y Treasury {market?.risk_free != null ? `${(market.risk_free * 100).toFixed(2)}%` : "—"}</div>
        </div>
      </div>

      <Banners warnings={[...company.warnings, ...(market?.warnings ?? [])]} />

      <Fundamentals company={company} />
      <Assumptions company={company} market={market} inputs={inputs} onChange={patch} />

      <div className="card">
        <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          <button onClick={() => void run()} disabled={running || missing.length > 0}>
            {running ? "Running…" : "Run DCF"}
          </button>
          {missing.length > 0 && (
            <span className="muted">Fill in: {missing.join(", ")}</span>
          )}
          <button className="ghost" onClick={() => void load(true)} style={{ marginLeft: "auto" }}>
            Refresh EDGAR data
          </button>
        </div>
        {runError && (
          <div style={{ marginTop: 12 }}>
            <Banners warnings={[runError]} kind="error" />
          </div>
        )}
      </div>

      {result && (
        <Verdict
          result={result}
          currentPrice={inputs.current_price ?? null}
          onSave={() => void save()}
          saving={saving}
          savedId={savedId}
        />
      )}
    </>
  );
}
