defmodule PhoenixAppWeb.MarketChannel do
  @moduledoc """
  Real-time market ticks per symbol.
  Topic format: "market:<symbol_lowercase>" e.g. "market:btcusdt"
  Fase 0: echo + cached last tick.
  Fase 1: subscribes to Phoenix.PubSub topic populated by Redis consumer.
  """
  use Phoenix.Channel

  alias PhoenixApp.Market.TickCache

  @impl true
  def join("market:" <> symbol, _payload, socket) do
    send(self(), {:after_join, symbol})
    {:ok, %{joined: symbol}, assign(socket, :symbol, symbol)}
  end

  @impl true
  def handle_info({:after_join, symbol}, socket) do
    case TickCache.get(String.upcase(symbol)) do
      nil -> :ok
      tick -> push(socket, "tick", tick)
    end

    {:noreply, socket}
  end

  @impl true
  def handle_in("ping", payload, socket) do
    {:reply, {:ok, Map.put(payload, :pong, true)}, socket}
  end
end
