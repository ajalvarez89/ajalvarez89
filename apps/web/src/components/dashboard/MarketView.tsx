"use client";

import { useState } from "react";
import { CandlestickChart } from "@/components/charts/CandlestickChart";
import { useMarketKlines } from "@/lib/hooks/useMarketKlines";

const SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"];
const INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d"];

function formatPrice(value: number | null | undefined): string {
  if (value == null) return "—";
  return value.toLocaleString("en-US", { maximumFractionDigits: 4 });
}

export function MarketView() {
  const [symbol, setSymbol] = useState<string>(SYMBOLS[0]);
  const [interval, setInterval] = useState<string>("1m");

  const { klines, lastTickPrice, status, error } = useMarketKlines(symbol, interval, 200);

  const last = klines[klines.length - 1];
  const change =
    klines.length > 1
      ? ((last.close - klines[0].open) / klines[0].open) * 100
      : 0;

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="flex gap-1">
          {SYMBOLS.map((s) => (
            <button
              key={s}
              onClick={() => setSymbol(s)}
              className={`px-3 py-1 text-sm rounded border ${
                symbol === s
                  ? "border-accent text-accent bg-accent/10"
                  : "border-border opacity-70 hover:opacity-100"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <div className="flex gap-1 ml-auto">
          {INTERVALS.map((tf) => (
            <button
              key={tf}
              onClick={() => setInterval(tf)}
              className={`px-2 py-1 text-xs rounded border ${
                interval === tf
                  ? "border-accent text-accent bg-accent/10"
                  : "border-border opacity-70 hover:opacity-100"
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-baseline gap-4 mb-3">
        <div>
          <div className="text-xs uppercase opacity-60">Last</div>
          <div className="text-2xl font-mono">
            {formatPrice(lastTickPrice ?? last?.close)}
          </div>
        </div>
        <div>
          <div className="text-xs uppercase opacity-60">Window change</div>
          <div className={`text-lg ${change >= 0 ? "text-positive" : "text-negative"}`}>
            {change >= 0 ? "+" : ""}
            {change.toFixed(2)}%
          </div>
        </div>
        <div>
          <div className="text-xs uppercase opacity-60">Status</div>
          <div className={`text-sm ${status === "ready" ? "text-positive" : status === "error" ? "text-negative" : "opacity-70"}`}>
            {status}
          </div>
        </div>
      </div>

      {error && <div className="text-negative text-sm mb-2">Error: {error}</div>}

      <CandlestickChart klines={klines} />
    </div>
  );
}
