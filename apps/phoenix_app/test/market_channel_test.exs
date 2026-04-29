defmodule PhoenixAppWeb.MarketChannelTest do
  use ExUnit.Case, async: true
  use Phoenix.ChannelTest

  @endpoint PhoenixAppWeb.Endpoint

  setup do
    {:ok, _, socket} =
      socket(PhoenixAppWeb.UserSocket, "user_id", %{})
      |> subscribe_and_join(PhoenixAppWeb.MarketChannel, "market:BTCUSDT")

    {:ok, socket: socket}
  end

  test "responds to ping", %{socket: socket} do
    ref = push(socket, "ping", %{"x" => 1})
    assert_reply ref, :ok, %{"x" => 1, pong: true}
  end

  test "forwards kline broadcast to client", %{socket: _socket} do
    Phoenix.PubSub.broadcast(PhoenixApp.PubSub, "market:BTCUSDT", {:kline, %{"symbol" => "BTCUSDT", "close" => 30000.0}})
    assert_push "kline", %{"symbol" => "BTCUSDT", "close" => 30000.0}
  end

  test "forwards tick broadcast to client", %{socket: _socket} do
    Phoenix.PubSub.broadcast(PhoenixApp.PubSub, "market:BTCUSDT", {:tick, %{"symbol" => "BTCUSDT", "price" => 30050.0}})
    assert_push "tick", %{"symbol" => "BTCUSDT", "price" => 30050.0}
  end
end
