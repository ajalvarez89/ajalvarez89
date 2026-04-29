"use client";

import { useEffect, useState } from "react";
import { fetchPositions, type Position } from "@/lib/trading-api";

export function OpenPositions() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const r = await fetchPositions();
        if (!cancelled) setPositions(r.positions);
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

  if (error) return <div className="text-negative text-sm">{error}</div>;
  if (positions.length === 0) return <div className="opacity-50 text-sm">No open positions.</div>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="opacity-60 text-xs uppercase">
          <tr className="border-b border-border">
            <th className="text-left py-2 pr-4">Symbol</th>
            <th className="text-left pr-4">Side</th>
            <th className="text-right pr-4">Qty</th>
            <th className="text-right pr-4">Entry</th>
            <th className="text-right pr-4">Realized</th>
            <th className="text-left pr-4">Strategy</th>
            <th className="text-left">Opened</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((p) => (
            <tr key={p.id} className="border-b border-border/40">
              <td className="py-2 pr-4 font-mono">{p.symbol}</td>
              <td className={`pr-4 ${p.side === "long" ? "text-positive" : "text-negative"}`}>{p.side}</td>
              <td className="text-right pr-4 font-mono">{p.quantity.toFixed(6)}</td>
              <td className="text-right pr-4 font-mono">{p.avg_entry_price.toFixed(2)}</td>
              <td className={`text-right pr-4 font-mono ${p.realized_pnl > 0 ? "text-positive" : p.realized_pnl < 0 ? "text-negative" : ""}`}>
                {p.realized_pnl.toFixed(2)}
              </td>
              <td className="pr-4 opacity-80">{p.strategy ?? "—"}</td>
              <td className="opacity-70">{new Date(p.opened_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
