"use client";

import { useEffect, useState } from "react";
import { getSocket } from "@/lib/phoenix-socket";

type Status = "connecting" | "open" | "closed";

export function ConnectionBadge() {
  const [status, setStatus] = useState<Status>("connecting");

  useEffect(() => {
    const socket = getSocket();
    const refs = [
      socket.onOpen(() => setStatus("open")),
      socket.onClose(() => setStatus("closed")),
      socket.onError(() => setStatus("closed")),
    ];
    return () => socket.off(refs);
  }, []);

  const color =
    status === "open" ? "bg-positive" : status === "connecting" ? "bg-yellow-400" : "bg-negative";
  const label =
    status === "open" ? "Connected" : status === "connecting" ? "Connecting..." : "Disconnected";

  return (
    <div className="flex items-center gap-2 text-sm">
      <span className={`inline-block w-2 h-2 rounded-full ${color}`} />
      <span>{label}</span>
    </div>
  );
}
