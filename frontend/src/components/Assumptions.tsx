import type { CompanyPayload, DcfInputs, MarketData } from "../api/types";
import { money, pct, price } from "../format";
import { NumberField } from "./NumberField";

interface Props {
  company: CompanyPayload;
  market: MarketData | null;
  inputs: Partial<DcfInputs>;
  onChange: (patch: Partial<DcfInputs>) => void;
}

export function Assumptions({ company, market, inputs, onChange }: Props) {
  const d = company.derived;
  const set = (key: keyof DcfInputs) => (value: number | null) => onChange({ [key]: value });

  const cagrs = [
    d.revenue_cagr_1y != null ? `1y ${pct(d.revenue_cagr_1y)}` : null,
    d.revenue_cagr_5y != null ? `5y ${pct(d.revenue_cagr_5y)}` : null,
    d.revenue_cagr_10y != null ? `10y ${pct(d.revenue_cagr_10y)}` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  const useOverride = inputs.wacc_override != null;

  return (
    <div className="card">
      <div className="section-label">2 · Your assumptions</div>
      <h2>Forecast drivers</h2>
      <p className="muted">
        Rates are annual decimals shown as %. Each input shows its historical anchor — you decide
        how the future differs from the past.
      </p>

      <div className="assumption-grid">
        <NumberField
          label="Revenue growth, years 1–5"
          anchor={cagrs ? `history: ${cagrs}` : "no revenue history"}
          value={inputs.growth_stage1 ?? null}
          onChange={set("growth_stage1")}
          kind="pct"
          missing
        />
        <NumberField
          label="Target operating margin (year 5+)"
          anchor={`latest ${pct(d.latest_operating_margin)} · 5y avg ${pct(d.avg_operating_margin_5y)}`}
          value={inputs.target_margin ?? null}
          onChange={set("target_margin")}
          kind="pct"
          missing
        />
        <NumberField
          label="Terminal growth"
          anchor={`capped at risk-free ${pct(market?.risk_free)}`}
          value={inputs.terminal_growth ?? null}
          onChange={set("terminal_growth")}
          kind="pct"
          missing
        />
        <NumberField
          label="Tax rate"
          anchor={`effective latest FY: ${pct(d.effective_tax_rate)}`}
          value={inputs.tax_rate ?? null}
          onChange={set("tax_rate")}
          kind="pct"
          missing
        />
        <NumberField
          label="Sales-to-capital ratio"
          anchor={
            d.sales_to_capital_5y != null
              ? `history 5y: ${d.sales_to_capital_5y.toFixed(2)}`
              : "not derivable from filings — 2.0 is a common default"
          }
          value={inputs.sales_to_capital ?? null}
          onChange={set("sales_to_capital")}
          kind="raw"
          missing
        />
        <NumberField
          label="Base revenue"
          anchor={`latest FY: ${money(d.latest_revenue)}`}
          value={inputs.base_revenue ?? null}
          onChange={set("base_revenue")}
          kind="millions"
          missing
        />
      </div>

      <h2 style={{ marginTop: 24 }}>Discount rate</h2>
      <p className="muted">
        WACC = cost of equity (rf + β × ERP) weighted by market cap, plus after-tax cost of debt
        weighted by debt. Set a direct override to skip the build-up.
      </p>
      <div className="assumption-grid">
        <NumberField
          label="Risk-free rate"
          anchor={`10Y Treasury: ${pct(market?.risk_free)}`}
          value={inputs.risk_free ?? null}
          onChange={set("risk_free")}
          kind="pct"
          missing={!useOverride}
        />
        <NumberField
          label="Beta"
          anchor={market?.beta != null ? `fetched: ${market.beta.toFixed(2)}` : "unavailable — 1.0 = market"}
          value={inputs.beta ?? null}
          onChange={set("beta")}
          kind="raw"
          missing={!useOverride}
        />
        <NumberField
          label="Equity risk premium"
          anchor="5.0% is a common US baseline"
          value={inputs.erp ?? null}
          onChange={set("erp")}
          kind="pct"
        />
        <NumberField
          label="Pre-tax cost of debt"
          anchor={`rf + spread; rf is ${pct(market?.risk_free)}`}
          value={inputs.pretax_cost_of_debt ?? null}
          onChange={set("pretax_cost_of_debt")}
          kind="pct"
          missing={!useOverride}
        />
        <NumberField
          label="WACC override (optional)"
          anchor="leave blank to use the build-up"
          value={inputs.wacc_override ?? null}
          onChange={set("wacc_override")}
          kind="pct"
        />
      </div>

      <h2 style={{ marginTop: 24 }}>Balance sheet & market</h2>
      <div className="assumption-grid">
        <NumberField
          label="Total debt"
          anchor={`latest filing: ${money(d.latest_total_debt)}`}
          value={inputs.total_debt ?? null}
          onChange={set("total_debt")}
          kind="millions"
          missing
        />
        <NumberField
          label="Cash & equivalents"
          anchor={`latest filing: ${money(d.latest_cash)}`}
          value={inputs.cash ?? null}
          onChange={set("cash")}
          kind="millions"
          missing
        />
        <NumberField
          label="Diluted shares (millions)"
          anchor="from latest 10-K"
          value={inputs.diluted_shares ?? null}
          onChange={set("diluted_shares")}
          kind="millions"
          missing
        />
        <NumberField
          label="Market cap"
          anchor="used for WACC weights"
          value={inputs.market_cap ?? null}
          onChange={set("market_cap")}
          kind="millions"
          missing={!useOverride}
        />
        <NumberField
          label="Current price"
          anchor={market?.price != null ? `fetched: ${price(market.price)}` : "feed unavailable"}
          value={inputs.current_price ?? null}
          onChange={set("current_price")}
          kind="raw"
        />
        <NumberField
          label="Current operating margin (base)"
          anchor={`latest FY: ${pct(d.latest_operating_margin)}`}
          value={inputs.base_margin ?? null}
          onChange={set("base_margin")}
          kind="pct"
          missing
        />
      </div>
    </div>
  );
}
