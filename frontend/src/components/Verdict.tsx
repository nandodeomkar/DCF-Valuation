import type { DcfResult } from "../api/types";
import { money, pct, price, signedPct } from "../format";
import { useCountUp } from "../hooks";
import { Banners } from "./Banners";

interface Props {
  result: DcfResult;
  currentPrice: number | null;
  onSave: () => void;
  saving: boolean;
  savedId: number | null;
  recalculating?: boolean;
}

/** Heatmap color for a sensitivity cell: green above market price, red below. */
function heatColor(cell: number | null, marketPrice: number | null, center: number): string {
  const reference = marketPrice ?? center;
  if (cell == null || reference <= 0) return "transparent";
  const ratio = cell / reference - 1;
  const intensity = Math.min(Math.abs(ratio) / 0.6, 1) * 0.32;
  return ratio >= 0
    ? `rgba(34, 197, 94, ${intensity.toFixed(3)})`
    : `rgba(239, 68, 68, ${intensity.toFixed(3)})`;
}

export function Verdict({ result, currentPrice, onSave, saving, savedId, recalculating }: Props) {
  const upside = result.upside;
  const animatedIntrinsic = useCountUp(result.intrinsic_per_share);
  const maxPv = Math.max(...result.years.map((y) => Math.abs(y.pv)), 1);

  return (
    <div className={`card fade-up${recalculating ? " recalculating" : ""}`}>
      <div className="section-label">3 · Verdict</div>
      <Banners warnings={result.warnings} />

      <div className="verdict">
        <div>
          <div className="muted">Intrinsic value / share</div>
          <div className="big">{price(animatedIntrinsic)}</div>
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
              <th style={{ textAlign: "left" }}>PV</th>
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
                <td className="num" style={{ textAlign: "left" }}>
                  <span
                    className="pv-bar"
                    style={{ width: `${Math.max((Math.abs(y.pv) / maxPv) * 60, 2)}px` }}
                  />
                  {money(y.pv)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 style={{ marginTop: 20 }}>Sensitivity — value per share</h2>
      <p className="muted">
        Rows: WACC. Columns: terminal growth. Green = above market price, red = below. Outlined
        cell = your base case.
      </p>
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
                  <td
                    key={j}
                    className={`heat${i === 2 && j === 2 ? " center-cell" : ""}`}
                    style={{
                      backgroundColor: heatColor(cell, currentPrice, result.intrinsic_per_share),
                    }}
                    title={cell == null ? "undefined (WACC ≤ g)" : price(cell)}
                  >
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
