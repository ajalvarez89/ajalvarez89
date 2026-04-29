"use client";

const API_URL = process.env.NEXT_PUBLIC_PHOENIX_API_URL || "http://localhost:4000/api";

export interface PnlWindow {
  realized_pnl: number;
  fees?: number;
  trades: number;
  winners?: number;
  losers?: number;
  win_rate?: number;
}

export type PnlResponse = Record<"day" | "week" | "month" | "year" | "all_time", PnlWindow>;

export interface Position {
  id: number;
  symbol: string;
  side: "long" | "short";
  quantity: number;
  avg_entry_price: number;
  unrealized_pnl: number;
  realized_pnl: number;
  strategy: string | null;
  mode: string;
  opened_at: string;
  closed_at: string | null;
}

export interface Order {
  id: number;
  external_id: string | null;
  symbol: string;
  side: "buy" | "sell";
  type: string;
  status: string;
  quantity: number | null;
  price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  strategy: string | null;
  mode: string;
  inserted_at: string;
}

export interface AdminStatus {
  kill_switch: { engaged: boolean; reason: string | null; engaged_at: string | null };
  approval: {
    id: number;
    actor: string;
    granted_at: string;
    expires_at: string;
  } | null;
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API_URL}${path}`, { cache: "no-store", ...init });
  if (!r.ok) throw new Error(`status ${r.status}`);
  return r.json();
}

export const fetchPnl = () => fetchJson<PnlResponse>("/trading/pnl");
export const fetchPositions = () => fetchJson<{ positions: Position[] }>("/trading/positions");
export const fetchOrders = (limit = 50) =>
  fetchJson<{ orders: Order[] }>(`/trading/orders?limit=${limit}`);
export const fetchAdminStatus = () => fetchJson<AdminStatus>("/admin/status");

export const approve = (ttlHours = 24) =>
  fetchJson<{ status: string; expires_at: string }>("/admin/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actor: "user", ttl_hours: ttlHours }),
  });

export const killSwitch = (reason = "manual") =>
  fetchJson<{ status: string; engaged: boolean }>("/admin/kill", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });

export const resume = () =>
  fetchJson<{ status: string; engaged: boolean }>("/admin/resume", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
