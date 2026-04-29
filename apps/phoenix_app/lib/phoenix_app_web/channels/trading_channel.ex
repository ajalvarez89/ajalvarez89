defmodule PhoenixAppWeb.TradingChannel do
  @moduledoc """
  Broadcasts P&L snapshots, position updates, and order events.
  Fase 0: stub that accepts joins and replies to pings.
  """
  use Phoenix.Channel

  @impl true
  def join("trading:lobby", _payload, socket) do
    {:ok, %{joined: "trading:lobby"}, socket}
  end

  @impl true
  def handle_in("ping", payload, socket) do
    {:reply, {:ok, Map.put(payload, :pong, true)}, socket}
  end
end
