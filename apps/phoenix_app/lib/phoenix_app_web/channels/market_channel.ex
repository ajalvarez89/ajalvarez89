defmodule PhoenixAppWeb.MarketChannel do
  @moduledoc """
  Real-time market data channel.

  Topic format: "market:<SYMBOL>" (uppercase), e.g. "market:BTCUSDT".
  After join, forwards events broadcast on Phoenix.PubSub by the
  `RedisConsumer` to the connected clients:

    - "tick"  -> payload from market.ticks (latest price)
    - "kline" -> payload from market.klines (candle, possibly in-progress)

  On join, replays the last cached tick if present so clients show price
  immediately without waiting for the next stream message.
  """
  use Phoenix.Channel

  alias Phoenix.PubSub
  alias PhoenixApp.Market.TickCache

  @pubsub PhoenixApp.PubSub

  @impl true
  def join("market:" <> symbol_raw, _payload, socket) do
    symbol = String.upcase(symbol_raw)
    PubSub.subscribe(@pubsub, "market:#{symbol}")
    send(self(), :replay_cache)
    {:ok, %{joined: symbol}, assign(socket, :symbol, symbol)}
  end

  @impl true
  def handle_info(:replay_cache, socket) do
    case TickCache.get(socket.assigns.symbol) do
      nil -> :ok
      tick -> push(socket, "tick", tick)
    end

    {:noreply, socket}
  end

  @impl true
  def handle_info({:tick, payload}, socket) do
    push(socket, "tick", payload)
    {:noreply, socket}
  end

  @impl true
  def handle_info({:kline, payload}, socket) do
    push(socket, "kline", payload)
    {:noreply, socket}
  end

  @impl true
  def handle_in("ping", payload, socket) do
    {:reply, {:ok, Map.put(payload, :pong, true)}, socket}
  end
end
