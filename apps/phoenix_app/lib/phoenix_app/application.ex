defmodule PhoenixApp.Application do
  @moduledoc false

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      PhoenixAppWeb.Telemetry,
      PhoenixApp.Repo,
      {Phoenix.PubSub, name: PhoenixApp.PubSub},
      {Redix, {Application.get_env(:phoenix_app, :redis_url, "redis://localhost:6379/0"), [name: :redix]}},
      PhoenixApp.Market.TickCache,
      PhoenixAppWeb.Endpoint
    ]

    opts = [strategy: :one_for_one, name: PhoenixApp.Supervisor]
    Supervisor.start_link(children, opts)
  end

  @impl true
  def config_change(changed, _new, removed) do
    PhoenixAppWeb.Endpoint.config_change(changed, removed)
    :ok
  end
end
