import Config

config :phoenix_app,
  ecto_repos: [PhoenixApp.Repo],
  generators: [timestamp_type: :utc_datetime]

config :phoenix_app, PhoenixAppWeb.Endpoint,
  url: [host: "localhost"],
  adapter: Bandit.PhoenixAdapter,
  render_errors: [
    formats: [json: PhoenixAppWeb.ErrorJSON],
    layout: false
  ],
  pubsub_server: PhoenixApp.PubSub,
  live_view: [signing_salt: "ctb_live_view_salt"]

config :phoenix_app, PhoenixApp.Repo,
  database: "data/sqlite/trading.db",
  pool_size: 5,
  show_sensitive_data_on_connection_error: false

config :logger, :console,
  format: "$time $metadata[$level] $message\n",
  metadata: [:request_id]

config :phoenix, :json_library, Jason

import_config "#{config_env()}.exs"
