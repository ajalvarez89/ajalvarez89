// Generated/maintained from /contracts/*.schema.json
// Phase 0: hand-written; Phase 1+ may switch to quicktype-based generation.

export interface MarketTick {
  symbol: string;
  timestamp_ms: number;
  price: number;
  volume?: number;
  bid?: number;
  ask?: number;
  source?: "binance" | "binance_testnet";
}

export interface TradingSignal {
  symbol: string;
  side: "buy" | "sell";
  strategy: string;
  confidence?: number;
  horizon_minutes?: number;
  target_price?: number;
  stop_loss?: number;
  take_profit?: number;
  atr?: number;
  metadata?: Record<string, unknown>;
  generated_at_ms: number;
}

export interface Order {
  external_id?: string | null;
  symbol: string;
  side: "buy" | "sell";
  type: "market" | "limit" | "stop_loss" | "take_profit" | "oco";
  status?: "new" | "submitted" | "partial" | "filled" | "canceled" | "rejected" | "expired";
  quantity: number;
  price?: number | null;
  stop_loss?: number | null;
  take_profit?: number | null;
  strategy?: string | null;
  mode: "testnet" | "paper" | "live";
  created_at_ms: number;
}

export interface Position {
  id?: number | string;
  symbol: string;
  side: "long" | "short";
  quantity: number;
  avg_entry_price: number;
  unrealized_pnl?: number;
  realized_pnl?: number;
  strategy?: string | null;
  mode: "testnet" | "paper" | "live";
  opened_at_ms: number;
  closed_at_ms?: number | null;
}

export interface NewsItem {
  id: string;
  source: string;
  title: string;
  url?: string | null;
  summary?: string | null;
  symbols?: string[];
  published_at_ms: number;
  sentiment?: {
    label: "positive" | "neutral" | "negative";
    score: number;
    model: string;
  } | null;
}

export interface PnLSnapshot {
  window: "day" | "week" | "month" | "year" | "all_time";
  starts_at_ms: number;
  ends_at_ms: number;
  realized_pnl: number;
  unrealized_pnl: number;
  fees?: number;
  trades?: number;
  winners?: number;
  losers?: number;
  win_rate?: number;
  max_drawdown_pct?: number;
}
