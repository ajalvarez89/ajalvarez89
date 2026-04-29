defmodule PhoenixApp.Bridges.TradingEngineClient do
  @moduledoc """
  Thin HTTP client to the Python `trading_engine` service.
  Used by web-facing controllers so the browser never talks to Python directly.
  """

  @default_timeout_ms 5_000

  def klines(symbol, opts \\ []) do
    interval = Keyword.get(opts, :interval, "1m")
    limit = Keyword.get(opts, :limit, 500)

    params =
      [symbol: symbol, interval: interval, limit: limit]
      |> maybe_put(:start_ms, Keyword.get(opts, :start_ms))
      |> maybe_put(:end_ms, Keyword.get(opts, :end_ms))

    case Req.get(base_url() <> "/market/klines",
           params: params,
           receive_timeout: @default_timeout_ms,
           connect_options: [timeout: @default_timeout_ms]
         ) do
      {:ok, %{status: 200, body: body}} -> {:ok, body}
      {:ok, %{status: status, body: body}} -> {:error, {:http, status, body}}
      {:error, reason} -> {:error, reason}
    end
  end

  defp base_url do
    Application.get_env(:phoenix_app, :trading_engine_url, "http://trading_engine:8001")
  end

  defp maybe_put(list, _key, nil), do: list
  defp maybe_put(list, key, value), do: list ++ [{key, value}]
end
