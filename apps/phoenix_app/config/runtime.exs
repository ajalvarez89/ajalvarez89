import Config

if config_env() == :prod do
  database_path =
    System.get_env("DATABASE_PATH") ||
      raise """
      environment variable DATABASE_PATH is missing.
      For example: /app/data/sqlite/trading.db
      """

  config :phoenix_app, PhoenixApp.Repo,
    database: database_path,
    pool_size: String.to_integer(System.get_env("POOL_SIZE") || "5")

  secret_key_base =
    System.get_env("SECRET_KEY_BASE") ||
      raise """
      environment variable SECRET_KEY_BASE is missing.
      Generate with: mix phx.gen.secret
      """

  host = System.get_env("PHX_HOST") || "localhost"
  port = String.to_integer(System.get_env("PHX_PORT") || "4000")

  config :phoenix_app, PhoenixAppWeb.Endpoint,
    url: [host: host, port: port, scheme: "http"],
    http: [ip: {0, 0, 0, 0, 0, 0, 0, 0}, port: port],
    secret_key_base: secret_key_base
end

# Common runtime config (applies to dev/prod)
config :phoenix_app, :redis_url, System.get_env("REDIS_URL", "redis://localhost:6379/0")
config :phoenix_app, :trading_engine_url, System.get_env("TRADING_ENGINE_URL", "http://trading_engine:8001")
config :phoenix_app, :ml_service_url, System.get_env("ML_SERVICE_URL", "http://ml_service:8002")
