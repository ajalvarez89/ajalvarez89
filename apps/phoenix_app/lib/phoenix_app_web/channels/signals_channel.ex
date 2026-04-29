defmodule PhoenixAppWeb.SignalsChannel do
  @moduledoc """
  ML signals feed.
  Fase 0: stub. Fase 3+: ingests from Redis Stream "signals".
  """
  use Phoenix.Channel

  @impl true
  def join("signals:lobby", _payload, socket) do
    {:ok, %{joined: "signals:lobby"}, socket}
  end

  @impl true
  def handle_in("ping", payload, socket) do
    {:reply, {:ok, Map.put(payload, :pong, true)}, socket}
  end
end
