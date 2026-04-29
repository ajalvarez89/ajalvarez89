"use client";

import { useEffect, useState } from "react";
import { fetchOrders, type Order } from "@/lib/trading-api";

export function RecentOrders() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const r = await fetchOrders(20);
        if (!cancelled) setOrders(r.orders);
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
  if (orders.length === 0) return <div className="opacity-50 text-sm">No orders yet.</div>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="opacity-60 text-xs uppercase">
          <tr className="border-b border-border">
            <th className="text-left py-2 pr-4">Time</th>
            <th className="text-left pr-4">Symbol</th>
            <th className="text-left pr-4">Side</th>
            <th className="text-right pr-4">Qty</th>
            <th className="text-right pr-4">Price</th>
            <th className="text-left pr-4">Mode</th>
            <th className="text-left">Status</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((o) => (
            <tr key={o.id} className="border-b border-border/40">
              <td className="py-2 pr-4 opacity-70">{new Date(o.inserted_at).toLocaleTimeString()}</td>
              <td className="pr-4 font-mono">{o.symbol}</td>
              <td className={`pr-4 ${o.side === "buy" ? "text-positive" : "text-negative"}`}>{o.side}</td>
              <td className="text-right pr-4 font-mono">{o.quantity?.toFixed(6) ?? "—"}</td>
              <td className="text-right pr-4 font-mono">{o.price?.toFixed(2) ?? "—"}</td>
              <td className="pr-4 opacity-80">{o.mode}</td>
              <td className="opacity-80">{o.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
