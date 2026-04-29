defmodule PhoenixApp.Bridges.ServiceProbe do
  @moduledoc """
  Lightweight HTTP probes used by the health/status endpoints.
  Avoids pulling a full HTTP client lib for Fase 0; uses `:httpc`.
  """

  def probe(url) when is_binary(url) do
    :inets.start()
    :ssl.start()

    case :httpc.request(:get, {String.to_charlist(url), []}, [{:timeout, 2000}], []) do
      {:ok, {{_, status, _}, _, _}} when status in 200..299 -> "ok"
      _ -> "down"
    end
  rescue
    _ -> "down"
  end

  def redis_ping do
    case Redix.command(:redix, ["PING"]) do
      {:ok, "PONG"} -> "ok"
      _ -> "down"
    end
  rescue
    _ -> "down"
  end
end
