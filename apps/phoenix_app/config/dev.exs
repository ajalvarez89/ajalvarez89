import Config

config :phoenix_app, PhoenixAppWeb.Endpoint,
  http: [ip: {0, 0, 0, 0}, port: 4000],
  check_origin: false,
  code_reloader: true,
  debug_errors: true,
  secret_key_base: "ctb_dev_secret_key_base_at_least_64_chars_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  watchers: []

config :phoenix_app, PhoenixApp.Repo,
  database: "/app/data/sqlite/trading.db",
  show_sensitive_data_on_connection_error: true,
  pool_size: 5

config :logger, :console, format: "[$level] $message\n"

config :phoenix, :stacktrace_depth, 20
config :phoenix, :plug_init_mode, :runtime
