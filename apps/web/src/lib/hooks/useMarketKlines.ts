"use client";

import { useEffect, useState } from "react";
import type { Channel } from "phoenix";
import { joinChannel } from "@/lib/phoenix-socket";

export interface Kline {
  symbol: string;
  interval: string;
  open_time_ms: number;
  close_time_ms: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  trades?: number;
  is_closed?: boolean;
}

const API_URL =
  process.env.NEXT_PUBLIC_PHOENIX_API_URL || "http://localhost:4000/api";

export interface UseMarketKlinesState {
  klines: Kline[];
  lastTickPrice: number | null;
  status: "loading" | "ready" | "error";
  error: string | null;
}

/**
 * Loads historical klines via REST then maintains them up-to-date via the
 * Phoenix MarketChannel. Open candles update in place; closed candles
 * append to the array.
 */
export function useMarketKlines(
  symbol: string,
  interval: string = "1m",
  limit: number = 200
): UseMarketKlinesState {
  const [klines, setKlines] = useState<Kline[]>([]);
  const [lastTickPrice, setLastTickPrice] = useState<number | null>(null);
  const [status, setStatus] = useState<UseMarketKlinesState["status"]>("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let channel: Channel | null = null;

    const upsertKline = (k: Kline) => {
      setKlines((prev) => {
        if (prev.length === 0) return [k];
        const last = prev[prev.length - 1];
        if (k.open_time_ms === last.open_time_ms) {
          // update in place
          const next = prev.slice(0, -1);
          next.push(k);
          return next;
        }
        if (k.open_time_ms > last.open_time_ms) {
          // new candle
          const next = [...prev, k];
          // keep buffer bounded
          if (next.length > limit + 200) return next.slice(-limit);
          return next;
        }
        return prev; // stale
      });
    };

    (async () => {
      try {
        const url = new URL(`${API_URL}/market/klines`);
        url.searchParams.set("symbol", symbol);
        url.searchParams.set("interval", interval);
        url.searchParams.set("limit", String(limit));
        const r = await fetch(url, { cache: "no-store" });
        if (!r.ok) throw new Error(`status ${r.status}`);
        const body = await r.json();
        if (cancelled) return;
        const initial: Kline[] = body.klines || [];
        setKlines(initial);
        if (initial.length > 0) setLastTickPrice(initial[initial.length - 1].close);
        setStatus("ready");
      } catch (e) {
        if (!cancelled) {
          setError(String(e));
          setStatus("error");
        }
      }

      if (cancelled) return;

      channel = joinChannel(`market:${symbol.toUpperCase()}`);
      channel.on("kline", (payload: Kline) => {
        if (payload.symbol !== symbol.toUpperCase()) return;
        if (payload.interval !== interval) return;
        upsertKline(payload);
      });
      channel.on("tick", (payload: { price: number; symbol: string }) => {
        if (payload.symbol !== symbol.toUpperCase()) return;
        setLastTickPrice(payload.price);
      });
    })();

    return () => {
      cancelled = true;
      channel?.leave();
    };
  }, [symbol, interval, limit]);

  return { klines, lastTickPrice, status, error };
}
