import type { DcfResult } from "../api/types";
import { money, pct, price, signedPct } from "../format";
import { Banners } from "./Banners";

interface Props {
  result: DcfResult;
  currentPrice: number | null;
  onSave: () => void;
  saving: boolean;
  savedId: number | null;
}

export function Verdict({ result, currentPrice, onSave, saving, savedId }: Props) {
  const upside = result.upside;

  return (
    <div className="card">
      <div className="section-label">3 · Verdict</div>
      <Banners warnings={result.warnings} />

      <div className="verdict">
        <div>
          <div className="muted">Intrinsic value / share</div>
          <div className="big">{price(result.intrinsic_per_share)}</div>
        </div>
        <div>
          <div className="muted">Market price</div>
          <div className="big" style={{ fontSize: 24 }}>
            {price(currentPrice)}
          </div>
        </div>
        {upside != null && (
          <span className={`badge ${upside >= 0 ? "up" : "down"}`}>
            {signedPct(upside)} {upside >= 0 ? "undervalued" : "overvalued"}
          </span>
        )}
        <div style={{ marginLeft: "auto" }}>
          <button onClick={onSave} disabled={saving || savedId != null}>
            {savedId != null ? "Saved ✓" : saving ? "Saving…" : "Save valuation"}
          </button>
        </div>
      </div>

      <div className="bridge">
        <div className="step">
          PV of FCFF (10y) <span className="v">{money(result.sum_pv_explicit)}</span>
        </div>
        <div className="step">
          + PV terminal <span className="v">{money(result.pv_terminal)}</span>
        </div>
        <div className="step">
          = Enterprise value <span className="v">{money(result.enterprise_value)}</span>
        </div>
        <div className="step">
          − Debt + Cash <span className="v">{money(result.equity_value - result.enterprise_value)}</span>
        </div>
        <div className="step">
          Equity value <span className="v">{money(result.equity_value)}</span>
        </div>
      </div>
      <p className="muted" style={{ marginTop: 8 }}>
        WACC {pct(result.wacc, 2)}
        {result.cost_of_equity != null && <> · cost of equity {pct(result.cost_of_equity, 2)}</>} ·
        terminal value is {pct(result.pv_terminal / result.enterprise_value)} of EV
      </p>

      <h2 style={{ marginTop: 20 }}>FCFF projection</h2>
      <div style={{ overflowX: "auto" }}>
        <table>
          <thead>
            <tr>
              <th>Year</th>
              <th>Revenue</th>
              <th>Growth</th>
              <th>Margin</th>
              <th>EBIT</th>
              <th>NOPAT</th>
              <th>Reinvest</th>
              <th>FCFF</th>
              <th>PV</th>
            </tr>
          </thead>
          <tbody>
            {result.years.map((y) => (
              <tr key={y.year}>
                <td>{y.year}</td>
                <td className="num">{money(y.revenue)}</td>
                <td className="num">{pct(y.growth)}</td>
                <td className="num">{pct(y.margin)}</td>
                <td className="num">{money(y.ebit)}</td>
                <td className="num">{money(y.nopat)}</td>
                <td className="num">{money(y.reinvestment)}</td>
                <td className="num">{money(y.fcff)}</td>
                <td className="num">{money(y.pv)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 style={{ marginTop: 20 }}>Sensitivity — value per share</h2>
      <p className="muted">Rows: WACC. Columns: terminal growth. Outlined cell = your base case.</p>
      <div style={{ overflowX: "auto" }}>
        <table className="sens">
          <thead>
            <tr>
              <th>WACC \ g</th>
              {result.sensitivity.growth_values.map((g) => (
                <th key={g}>{pct(g, 2)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {result.sensitivity.matrix.map((row, i) => (
              <tr key={result.sensitivity.wacc_values[i]}>
                <td className="num">{pct(result.sensitivity.wacc_values[i], 2)}</td>
                {row.map((cell, j) => (
                  <td key={j} className={i === 2 && j === 2 ? "center-cell" : ""}>
                    {cell == null ? "—" : price(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
