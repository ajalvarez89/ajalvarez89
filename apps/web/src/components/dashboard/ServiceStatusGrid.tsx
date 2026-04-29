"use client";

import { useEffect, useState } from "react";
import { fetchServicesStatus } from "@/lib/api-client";

export function ServiceStatusGrid() {
  const [statuses, setStatuses] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await fetchServicesStatus();
        if (!cancelled) setStatuses(data);
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

  if (error) return <div className="text-negative text-sm">Error: {error}</div>;

  const entries = Object.entries(statuses);
  if (entries.length === 0) return <div className="opacity-50 text-sm">Loading...</div>;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {entries.map(([name, status]) => {
        const ok = status === "ok";
        return (
          <div
            key={name}
            className="border border-border rounded p-3 flex flex-col gap-1"
          >
            <span className="text-xs uppercase opacity-60">{name}</span>
            <span className={`text-sm font-semibold ${ok ? "text-positive" : "text-negative"}`}>
              {status}
            </span>
          </div>
        );
      })}
    </div>
  );
}
