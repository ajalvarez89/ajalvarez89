defmodule PhoenixAppWeb.HealthController do
  use Phoenix.Controller, formats: [:json]

  alias PhoenixApp.Bridges.ServiceProbe

  def show(conn, _params) do
    json(conn, %{status: "ok", service: "phoenix_app", version: "0.1.0"})
  end

  def services_status(conn, _params) do
    statuses = %{
      phoenix_app: "ok",
      trading_engine: ServiceProbe.probe(Application.get_env(:phoenix_app, :trading_engine_url) <> "/health"),
      ml_service: ServiceProbe.probe(Application.get_env(:phoenix_app, :ml_service_url) <> "/health"),
      redis: ServiceProbe.redis_ping()
    }

    json(conn, statuses)
  end
end
