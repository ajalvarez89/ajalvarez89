"use client";

import { Socket, type Channel } from "phoenix";

const WS_URL = process.env.NEXT_PUBLIC_PHOENIX_WS_URL || "ws://localhost:4000/socket";

let socket: Socket | null = null;

export function getSocket(): Socket {
  if (socket) return socket;
  socket = new Socket(WS_URL, {
    logger: (kind, msg, data) => {
      // eslint-disable-next-line no-console
      console.debug(`phx ${kind}: ${msg}`, data);
    },
  });
  socket.connect();
  return socket;
}

export function joinChannel(topic: string, params: object = {}): Channel {
  const s = getSocket();
  const channel = s.channel(topic, params);
  channel.join().receive("error", (resp) => {
    // eslint-disable-next-line no-console
    console.warn(`Failed to join ${topic}`, resp);
  });
  return channel;
}
