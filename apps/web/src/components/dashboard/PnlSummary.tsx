"use client";

import { useEffect, useState } from "react";
import { fetchPnl, type PnlResponse } from "@/lib/trading-api";

const WINDOWS: { key: keyof PnlResponse; label: string }[] = [
  { key: "day", label: "Day" },
  { key: "week", label: "Week" },
  { key: "month", label: "Month" },
  { key: "year", label: "Year" },
  { key: "all_time", label: "All time" },
];

function fmt(n: number | undefined): string {
  if (n == null) return "—";
  return n.toLocaleString("en-US", { maximumFractionDigits: 2 });
}

export function PnlSummary() {
  const [data, setData] = useState<PnlResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const d = await fetchPnl();
        if (!cancelled) setData(d);
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

  if (error) return <div className="text-negative text-sm">PnL error: {error}</div>;
  if (!data) return <div className="opacity-50 text-sm">Loading PnL...</div>;

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {WINDOWS.map(({ key, label }) => {
        const w = data[key];
        const pnl = w?.realized_pnl ?? 0;
        const colour = pnl > 0 ? "text-positive" : pnl < 0 ? "text-negative" : "opacity-70";
        return (
          <div key={key} className="border border-border rounded p-3">
            <div className="text-xs uppercase opacity-60">{label}</div>
            <div className={`text-lg font-mono ${colour}`}>
              {pnl >= 0 ? "+" : ""}
              {fmt(pnl)}
            </div>
            <div className="text-xs opacity-60">
              {w?.trades ?? 0} trades · {w?.winners ?? 0}/{w?.losers ?? 0} W/L · {((w?.win_rate ?? 0) * 100).toFixed(0)}% win
            </div>
          </div>
        );
      })}
    </div>
  );
}
