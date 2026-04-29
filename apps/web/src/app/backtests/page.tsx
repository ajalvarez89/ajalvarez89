"use client";

import { useEffect, useState } from "react";

interface BacktestResult {
  symbol: string;
  total_return_pct: number;
  sharpe: number;
  sortino: number;
  max_drawdown_pct: number;
  profit_factor: number;
  win_rate: number;
  n_trades: number;
  drawdown_band: "green" | "amber" | "red";
}

interface BacktestRun {
  id: string;
  timestamp: string;
  interval: string;
  results: BacktestResult[];
}

const ML_URL = process.env.NEXT_PUBLIC_ML_SERVICE_URL || "http://localhost:8002";

export default function BacktestsPage() {
  const [runs, setRuns] = useState<BacktestRun[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const r = await fetch(`${ML_URL}/backtests`, { cache: "no-store" });
        if (!r.ok) throw new Error(`status ${r.status}`);
        const body = await r.json();
        if (!cancelled) setRuns(body.runs || []);
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    };
    load();
    const id = setInterval(load, 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const colour = (band: string) =>
    band === "green" ? "text-positive" : band === "amber" ? "text-yellow-400" : "text-negative";

  return (
    <main>
      <header className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-accent">Backtests</h1>
          <p className="text-sm opacity-70">
            Drawdown semaforizado: 🟢 &lt;20% · 🟠 20-30% · 🔴 &gt;30%
          </p>
        </div>
        <a href="/" className="text-sm opacity-70 hover:text-accent">← back to dashboard</a>
      </header>

      {error ? <div className="text-negative text-sm mb-4">{error}</div> : null}

      {runs.length === 0 ? (
        <div className="opacity-50 text-sm">
          No backtests yet. Run <code className="bg-panel px-2 py-1 rounded">make backtest</code>.
        </div>
      ) : (
        <div className="space-y-6">
          {runs.map((run) => (
            <div key={run.id} className="bg-panel border border-border rounded-lg p-5">
              <div className="flex items-baseline justify-between mb-3">
                <h2 className="text-lg font-semibold">{run.timestamp}</h2>
                <span className="text-xs opacity-60">interval {run.interval}</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="opacity-60 text-xs uppercase">
                    <tr className="border-b border-border">
                      <th className="text-left py-2 pr-4">Symbol</th>
                      <th className="text-right pr-4">Return</th>
                      <th className="text-right pr-4">Sharpe</th>
                      <th className="text-right pr-4">Max DD</th>
                      <th className="text-right pr-4">PF</th>
                      <th className="text-right pr-4">Win rate</th>
                      <th className="text-right pr-4">Trades</th>
                      <th className="text-left">Band</th>
                    </tr>
                  </thead>
                  <tbody>
                    {run.results.map((r) => (
                      <tr key={r.symbol} className="border-b border-border/40">
                        <td className="py-2 pr-4 font-mono">{r.symbol}</td>
                        <td className={`text-right pr-4 font-mono ${r.total_return_pct >= 0 ? "text-positive" : "text-negative"}`}>
                          {r.total_return_pct.toFixed(2)}%
                        </td>
                        <td className="text-right pr-4 font-mono">{r.sharpe.toFixed(2)}</td>
                        <td className="text-right pr-4 font-mono">{r.max_drawdown_pct.toFixed(2)}%</td>
                        <td className="text-right pr-4 font-mono">{r.profit_factor.toFixed(2)}</td>
                        <td className="text-right pr-4 font-mono">{(r.win_rate * 100).toFixed(0)}%</td>
                        <td className="text-right pr-4 font-mono">{r.n_trades}</td>
                        <td className={`uppercase ${colour(r.drawdown_band)}`}>{r.drawdown_band}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
