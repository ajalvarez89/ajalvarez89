"use client";

import { useEffect, useState } from "react";
import type { Channel } from "phoenix";
import { joinChannel } from "@/lib/phoenix-socket";

interface NewsItem {
  id: string | number;
  source: string;
  title: string;
  url: string | null;
  symbols: string[];
  published_at_ms: number;
  sentiment?: { label: "positive" | "neutral" | "negative"; score: number; model: string } | null;
}

const API_URL = process.env.NEXT_PUBLIC_PHOENIX_API_URL || "http://localhost:4000/api";

function badge(label: NewsItem["sentiment"] extends infer T ? (T extends { label: infer L } ? L : never) : never | undefined) {
  if (!label) return "border-border opacity-70";
  if (label === "positive") return "border-positive text-positive";
  if (label === "negative") return "border-negative text-negative";
  return "border-border opacity-70";
}

export function NewsFeed() {
  const [items, setItems] = useState<NewsItem[]>([]);

  useEffect(() => {
    let cancelled = false;
    let channel: Channel | null = null;

    (async () => {
      try {
        const r = await fetch(`${API_URL}/news?limit=50`, { cache: "no-store" });
        if (r.ok) {
          const body = await r.json();
          if (!cancelled) setItems(body.items || []);
        }
      } catch {
        // ignore — channel will populate
      }

      if (cancelled) return;

      channel = joinChannel("news:lobby");
      channel.on("snapshot", (payload: { items: NewsItem[] }) => {
        if (!cancelled) setItems(payload.items || []);
      });
      channel.on("item", (item: NewsItem) => {
        if (cancelled) return;
        setItems((prev) => [item, ...prev].slice(0, 50));
      });
    })();

    return () => {
      cancelled = true;
      channel?.leave();
    };
  }, []);

  if (items.length === 0) {
    return <div className="opacity-50 text-sm">No news yet. (Set CRYPTOPANIC_API_KEY in .env to enable polling.)</div>;
  }

  return (
    <ul className="space-y-2 max-h-[420px] overflow-y-auto">
      {items.map((item, i) => {
        const label = item.sentiment?.label;
        const score = item.sentiment?.score;
        return (
          <li key={`${item.id}-${i}`} className="border-b border-border/30 pb-2">
            <div className="flex items-center gap-2 text-xs opacity-60 mb-1">
              <span className="uppercase">{item.source}</span>
              {item.symbols?.length ? <span>· {item.symbols.join(", ")}</span> : null}
              <span>· {new Date(item.published_at_ms).toLocaleTimeString()}</span>
              {label ? (
                <span className={`ml-auto border rounded px-2 py-0.5 ${badge(label)}`}>
                  {label}
                  {typeof score === "number" ? ` · ${score.toFixed(2)}` : ""}
                </span>
              ) : null}
            </div>
            <div className="text-sm">
              {item.url ? (
                <a href={item.url} target="_blank" rel="noreferrer" className="hover:text-accent">
                  {item.title}
                </a>
              ) : (
                item.title
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
