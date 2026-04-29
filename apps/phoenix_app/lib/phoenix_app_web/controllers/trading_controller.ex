defmodule PhoenixAppWeb.TradingController do
  @moduledoc "Read-only trading dashboards: orders, positions, trades, PnL."
  use Phoenix.Controller, formats: [:json]

  alias PhoenixApp.Bridges.TradingEngineClient

  def orders(conn, params) do
    limit = parse_int(params["limit"], 50)
    proxy(conn, fn -> TradingEngineClient.list_orders(limit) end)
  end

  def positions(conn, _params), do: proxy(conn, &TradingEngineClient.list_positions/0)
  def trades(conn, params) do
    limit = parse_int(params["limit"], 100)
    proxy(conn, fn -> TradingEngineClient.list_trades(limit) end)
  end

  def pnl(conn, _params), do: proxy(conn, &TradingEngineClient.pnl/0)
  def strategies(conn, _params), do: proxy(conn, &TradingEngineClient.list_strategies/0)

  defp proxy(conn, fun) do
    case fun.() do
      {:ok, body} -> json(conn, body)
      {:error, err} -> conn |> put_status(:bad_gateway) |> json(%{error: inspect(err)})
    end
  end

  defp parse_int(nil, default), do: default
  defp parse_int(v, _) when is_integer(v), do: v
  defp parse_int(v, default) when is_binary(v) do
    case Integer.parse(v) do
      {n, ""} when n > 0 -> n
      _ -> default
    end
  end
end
