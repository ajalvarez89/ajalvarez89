defmodule PhoenixAppWeb.AdminController do
  @moduledoc """
  User-facing admin endpoints (approve, kill, resume).
  Forwards to trading_engine which owns the persistence and gates execution.
  """
  use Phoenix.Controller, formats: [:json]

  alias PhoenixApp.Bridges.TradingEngineClient

  def approve(conn, params) do
    actor = Map.get(params, "actor", "user")
    ttl = parse_int(Map.get(params, "ttl_hours"), 24)

    case TradingEngineClient.approve(actor, ttl) do
      {:ok, body} -> json(conn, body)
      {:error, reason} -> conn |> put_status(:bad_gateway) |> json(%{error: inspect(reason)})
    end
  end

  def kill(conn, params) do
    reason = Map.get(params, "reason", "manual")

    case TradingEngineClient.kill(reason) do
      {:ok, body} -> json(conn, body)
      {:error, err} -> conn |> put_status(:bad_gateway) |> json(%{error: inspect(err)})
    end
  end

  def resume(conn, _params) do
    case TradingEngineClient.resume() do
      {:ok, body} -> json(conn, body)
      {:error, err} -> conn |> put_status(:bad_gateway) |> json(%{error: inspect(err)})
    end
  end

  def status(conn, _params) do
    case TradingEngineClient.admin_status() do
      {:ok, body} -> json(conn, body)
      {:error, err} -> conn |> put_status(:bad_gateway) |> json(%{error: inspect(err)})
    end
  end

  defp parse_int(nil, default), do: default
  defp parse_int(v, _) when is_integer(v), do: v
  defp parse_int(v, default) when is_binary(v) do
    case Integer.parse(v) do
      {n, ""} -> n
      _ -> default
    end
  end
end
