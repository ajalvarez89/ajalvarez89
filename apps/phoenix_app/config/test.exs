import Config

config :phoenix_app, PhoenixApp.Repo,
  database: ":memory:",
  pool: Ecto.Adapters.SQL.Sandbox

config :phoenix_app, PhoenixAppWeb.Endpoint,
  http: [ip: {127, 0, 0, 1}, port: 4002],
  secret_key_base: "ctb_test_secret_key_base_at_least_64_chars_yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy",
  server: false

config :logger, level: :warning
config :phoenix, :plug_init_mode, :runtime
