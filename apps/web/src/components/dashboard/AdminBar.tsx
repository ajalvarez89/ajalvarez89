"use client";

import { useEffect, useState } from "react";
import { approve, fetchAdminStatus, killSwitch, resume, type AdminStatus } from "@/lib/trading-api";

export function AdminBar() {
  const [status, setStatus] = useState<AdminStatus | null>(null);
  const [busy, setBusy] = useState<boolean>(false);
  const [confirmKill, setConfirmKill] = useState<boolean>(false);

  const refresh = async () => {
    try {
      const s = await fetchAdminStatus();
      setStatus(s);
    } catch {
      setStatus(null);
    }
  };

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, []);

  const onApprove = async () => {
    setBusy(true);
    try {
      await approve(24);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const onKill = async () => {
    if (!confirmKill) {
      setConfirmKill(true);
      setTimeout(() => setConfirmKill(false), 5000);
      return;
    }
    setBusy(true);
    try {
      await killSwitch("ui_button");
      await refresh();
    } finally {
      setBusy(false);
      setConfirmKill(false);
    }
  };

  const onResume = async () => {
    setBusy(true);
    try {
      await resume();
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const engaged = status?.kill_switch.engaged;
  const approvalExpiresAt = status?.approval?.expires_at ?? null;
  const hoursLeft = approvalExpiresAt
    ? Math.max(0, (new Date(approvalExpiresAt).getTime() - Date.now()) / (1000 * 60 * 60))
    : 0;

  return (
    <div className="flex flex-wrap items-center gap-3 text-sm">
      <div>
        <span className="opacity-60 mr-2">Approval:</span>
        {status?.approval ? (
          <span className="text-positive">active · {hoursLeft.toFixed(1)}h left</span>
        ) : (
          <span className="text-negative">none</span>
        )}
      </div>
      <div>
        <span className="opacity-60 mr-2">Kill switch:</span>
        {engaged ? (
          <span className="text-negative font-semibold">ENGAGED</span>
        ) : (
          <span className="text-positive">off</span>
        )}
      </div>

      <div className="ml-auto flex gap-2">
        <button
          onClick={onApprove}
          disabled={busy}
          className="border border-border rounded px-3 py-1 hover:border-accent hover:text-accent disabled:opacity-50"
        >
          Approve 24h
        </button>
        {!engaged ? (
          <button
            onClick={onKill}
            disabled={busy}
            className={`border rounded px-3 py-1 disabled:opacity-50 ${
              confirmKill ? "border-negative bg-negative/10 text-negative" : "border-negative text-negative hover:bg-negative/10"
            }`}
          >
            {confirmKill ? "Click again to confirm" : "Kill switch"}
          </button>
        ) : (
          <button
            onClick={onResume}
            disabled={busy}
            className="border border-accent rounded px-3 py-1 text-accent hover:bg-accent/10 disabled:opacity-50"
          >
            Resume
          </button>
        )}
      </div>
    </div>
  );
}
