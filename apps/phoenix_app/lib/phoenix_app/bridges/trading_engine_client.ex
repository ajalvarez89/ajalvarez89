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

    get_json("/market/klines", params: params)
  end

  def list_orders(limit \\ 50), do: get_json("/orders", params: [limit: limit])
  def list_positions, do: get_json("/orders/positions")
  def list_trades(limit \\ 100), do: get_json("/orders/trades", params: [limit: limit])
  def pnl, do: get_json("/orders/pnl")
  def admin_status, do: get_json("/admin/status")
  def list_strategies, do: get_json("/strategies")

  def approve(actor, ttl_hours \\ 24),
    do: post_json("/admin/approve", %{actor: actor, ttl_hours: ttl_hours})

  def kill(reason \\ "manual"), do: post_json("/admin/kill", %{reason: reason})
  def resume, do: post_json("/admin/resume", %{})

  def toggle_strategy(name, enabled),
    do: post_json("/strategies/#{name}/toggle", %{enabled: enabled})

  def list_backtests do
    case Req.get(ml_service_url() <> "/backtests", receive_timeout: @default_timeout_ms) do
      {:ok, %{status: 200, body: body}} -> {:ok, body}
      {:ok, %{status: status, body: body}} -> {:error, {:http, status, body}}
      {:error, reason} -> {:error, reason}
    end
  end

  # ---------------------------------------------------------------------------

  defp get_json(path, opts \\ []) do
    case Req.get(base_url() <> path, Keyword.merge([receive_timeout: @default_timeout_ms], opts)) do
      {:ok, %{status: 200, body: body}} -> {:ok, body}
      {:ok, %{status: status, body: body}} -> {:error, {:http, status, body}}
      {:error, reason} -> {:error, reason}
    end
  end

  defp post_json(path, body) do
    case Req.post(base_url() <> path, json: body, receive_timeout: @default_timeout_ms) do
      {:ok, %{status: status, body: resp}} when status in 200..299 -> {:ok, resp}
      {:ok, %{status: status, body: resp}} -> {:error, {:http, status, resp}}
      {:error, reason} -> {:error, reason}
    end
  end

  defp base_url do
    Application.get_env(:phoenix_app, :trading_engine_url, "http://trading_engine:8001")
  end

  defp ml_service_url do
    Application.get_env(:phoenix_app, :ml_service_url, "http://ml_service:8002")
  end

  defp maybe_put(list, _key, nil), do: list
  defp maybe_put(list, key, value), do: list ++ [{key, value}]
end
