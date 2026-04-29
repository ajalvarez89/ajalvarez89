defmodule PhoenixAppWeb.MarketController do
  use Phoenix.Controller, formats: [:json]

  alias PhoenixApp.Bridges.TradingEngineClient

  @valid_intervals ~w(1m 3m 5m 15m 30m 1h 2h 4h 6h 8h 12h 1d 3d 1w 1M)

  def klines(conn, %{"symbol" => symbol} = params) do
    interval = Map.get(params, "interval", "1m")
    limit = parse_int(Map.get(params, "limit"), 500)

    cond do
      interval not in @valid_intervals ->
        conn
        |> put_status(:bad_request)
        |> json(%{error: "invalid_interval", allowed: @valid_intervals})

      true ->
        case TradingEngineClient.klines(symbol,
               interval: interval,
               limit: limit
             ) do
          {:ok, body} ->
            json(conn, body)

          {:error, reason} ->
            conn
            |> put_status(:bad_gateway)
            |> json(%{error: "trading_engine_unreachable", detail: inspect(reason)})
        end
    end
  end

  def klines(conn, _params) do
    conn
    |> put_status(:bad_request)
    |> json(%{error: "missing_symbol"})
  end

  defp parse_int(nil, default), do: default
  defp parse_int(v, default) when is_integer(v), do: v
  defp parse_int(v, default) when is_binary(v) do
    case Integer.parse(v) do
      {n, ""} when n > 0 and n <= 1000 -> n
      _ -> default
    end
  end
end
