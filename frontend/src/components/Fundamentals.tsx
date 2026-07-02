import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CompanyPayload } from "../api/types";
import { money, pct, shares } from "../format";

const ROWS: { key: keyof CompanyPayload["years"][number]; label: string; fmt: (v: number | null) => string }[] = [
  { key: "revenue", label: "Revenue", fmt: (v) => money(v) },
  { key: "operating_income", label: "Operating income", fmt: (v) => money(v) },
  { key: "depreciation_amortization", label: "D&A", fmt: (v) => money(v) },
  { key: "capex", label: "Capex", fmt: (v) => money(v) },
  { key: "working_capital", label: "Working capital", fmt: (v) => money(v) },
  { key: "total_debt", label: "Total debt", fmt: (v) => money(v) },
  { key: "cash", label: "Cash", fmt: (v) => money(v) },
  { key: "diluted_shares", label: "Diluted shares", fmt: (v) => shares(v) },
];

export function Fundamentals({ company }: { company: CompanyPayload }) {
  const years = company.years;
  const chartData = years
    .filter((y) => y.revenue != null)
    .map((y) => ({
      year: y.fiscal_year,
      revenueB: (y.revenue ?? 0) / 1e9,
      margin:
        y.revenue && y.operating_income != null ? (y.operating_income / y.revenue) * 100 : null,
    }));

  return (
    <div className="card">
      <div className="section-label">1 · What EDGAR says</div>
      <h2>
        Fundamentals, FY{years[0]?.fiscal_year}–FY{years[years.length - 1]?.fiscal_year}
      </h2>
      <p className="muted">
        Annual 10-K data from SEC EDGAR (CIK {company.cik}). Derived anchors from this history
        pre-fill the assumptions below.
      </p>

      {chartData.length > 1 && (
        <ResponsiveContainer width="100%" height={220}>
          <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="var(--border)" vertical={false} />
            <XAxis dataKey="year" tick={{ fontSize: 12 }} />
            <YAxis
              yAxisId="rev"
              tick={{ fontSize: 12 }}
              tickFormatter={(v: number) => `$${v.toFixed(0)}B`}
            />
            <YAxis
              yAxisId="margin"
              orientation="right"
              tick={{ fontSize: 12 }}
              tickFormatter={(v: number) => `${v.toFixed(0)}%`}
            />
            <Tooltip
              contentStyle={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                color: "var(--text)",
              }}
              formatter={(value, name) =>
                name === "Revenue ($B)"
                  ? [`$${Number(value).toFixed(1)}B`, "Revenue"]
                  : [`${Number(value).toFixed(1)}%`, "Op margin"]
              }
            />
            <Bar
              yAxisId="rev"
              dataKey="revenueB"
              name="Revenue ($B)"
              fill="var(--chart-bar)"
              radius={[3, 3, 0, 0]}
              animationDuration={700}
            />
            <Line
              yAxisId="margin"
              dataKey="margin"
              name="Op margin (%)"
              stroke="var(--chart-line)"
              strokeWidth={2}
              dot={false}
              animationDuration={900}
            />
          </ComposedChart>
        </ResponsiveContainer>
      )}

      <div style={{ overflowX: "auto", marginTop: 12 }}>
        <table>
          <thead>
            <tr>
              <th>FY</th>
              {years.map((y) => (
                <th key={y.end_date}>{y.fiscal_year}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ROWS.map((row) => (
              <tr key={row.key}>
                <td>{row.label}</td>
                {years.map((y) => (
                  <td key={y.end_date} className="num">
                    {row.fmt(y[row.key] as number | null)}
                  </td>
                ))}
              </tr>
            ))}
            <tr>
              <td>Op margin</td>
              {years.map((y) => (
                <td key={y.end_date} className="num">
                  {y.revenue && y.operating_income != null
                    ? pct(y.operating_income / y.revenue)
                    : "—"}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
