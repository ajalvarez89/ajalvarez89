const API_URL = process.env.NEXT_PUBLIC_PHOENIX_API_URL || "http://localhost:4000/api";

export async function fetchServicesStatus(): Promise<Record<string, string>> {
  const r = await fetch(`${API_URL}/services/status`, { cache: "no-store" });
  if (!r.ok) throw new Error(`status ${r.status}`);
  return r.json();
}
