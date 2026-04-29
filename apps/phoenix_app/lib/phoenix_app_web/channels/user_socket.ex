defmodule PhoenixAppWeb.UserSocket do
  use Phoenix.Socket

  channel "market:*", PhoenixAppWeb.MarketChannel
  channel "trading:*", PhoenixAppWeb.TradingChannel
  channel "signals:*", PhoenixAppWeb.SignalsChannel

  @impl true
  def connect(_params, socket, _connect_info) do
    {:ok, socket}
  end

  @impl true
  def id(_socket), do: nil
end
