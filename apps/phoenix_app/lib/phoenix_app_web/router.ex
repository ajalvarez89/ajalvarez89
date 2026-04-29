defmodule PhoenixAppWeb.Router do
  use Phoenix.Router

  import Plug.Conn
  import Phoenix.Controller

  pipeline :api do
    plug :accepts, ["json"]
  end

  scope "/", PhoenixAppWeb do
    get "/health", HealthController, :show
  end

  scope "/api", PhoenixAppWeb do
    pipe_through :api

    get "/health", HealthController, :show
    get "/services/status", HealthController, :services_status
    get "/market/klines", MarketController, :klines
    post "/admin/approve", AdminController, :approve
    post "/admin/kill", AdminController, :kill
    post "/admin/resume", AdminController, :resume
    get "/admin/status", AdminController, :status

    get "/trading/orders", TradingController, :orders
    get "/trading/positions", TradingController, :positions
    get "/trading/trades", TradingController, :trades
    get "/trading/pnl", TradingController, :pnl
    get "/trading/strategies", TradingController, :strategies
  end
end
