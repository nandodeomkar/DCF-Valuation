import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { SavedValuation } from "../api/types";
import { Banners } from "../components/Banners";
import { price, signedPct } from "../format";

export function Home() {
  const [valuations, setValuations] = useState<SavedValuation[] | null>(null);
  const [prices, setPrices] = useState<Record<string, number | null>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listValuations()
      .then((list) => {
        setValuations(list);
        const tickers = [...new Set(list.map((v) => v.ticker))];
        tickers.forEach((t) => {
          api
            .market(t)
            .then((m) => setPrices((prev) => ({ ...prev, [t]: m.price })))
            .catch(() => setPrices((prev) => ({ ...prev, [t]: null })));
        });
      })
      .catch((e) => setError(`Could not reach the backend: ${e}`));
  }, []);

  const remove = async (id: number) => {
    await api.deleteValuation(id);
    setValuations((prev) => (prev ? prev.filter((v) => v.id !== id) : prev));
  };

  if (error) return <Banners warnings={[error]} kind="error" />;
  if (valuations === null) return <div className="spinner">Loading saved valuations…</div>;

  return (
    <div className="card">
      <div className="section-label">Saved valuations</div>
      {valuations.length === 0 ? (
        <p className="muted">
          Nothing saved yet. Search a US ticker above (e.g. AAPL, MSFT, COST) to fetch its EDGAR
          fundamentals and run your first DCF.
        </p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Company</th>
              <th>Date</th>
              <th>Intrinsic</th>
              <th>Price then</th>
              <th>Price now</th>
              <th>Upside now</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {valuations.map((v) => {
              const now = prices[v.ticker];
              const upsideNow = now ? v.result.intrinsic_per_share / now - 1 : null;
              return (
                <tr key={v.id}>
                  <td>
                    <Link to={`/company/${v.ticker}`}>
                      {v.company_name} ({v.ticker})
                    </Link>
                  </td>
                  <td className="num">{v.created_at ? v.created_at.slice(0, 10) : "—"}</td>
                  <td className="num">{price(v.result.intrinsic_per_share)}</td>
                  <td className="num">{price(v.price_at_run)}</td>
                  <td className="num">{now === undefined ? "…" : price(now)}</td>
                  <td className="num">
                    {upsideNow == null ? (
                      "—"
                    ) : (
                      <span className={`badge ${upsideNow >= 0 ? "up" : "down"}`} style={{ fontSize: 12 }}>
                        {signedPct(upsideNow)}
                      </span>
                    )}
                  </td>
                  <td>
                    <button className="danger" onClick={() => v.id != null && void remove(v.id)}>
                      Delete
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      <p className="footer-note">
        Fundamentals: SEC EDGAR (10-K XBRL) · Price/beta: Yahoo Finance · Risk-free: FRED 10Y
        Treasury. Personal tool — assumptions are yours, not advice.
      </p>
    </div>
  );
}
