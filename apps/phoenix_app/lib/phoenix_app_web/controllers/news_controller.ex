defmodule PhoenixAppWeb.NewsController do
  use Phoenix.Controller, formats: [:json]

  alias PhoenixApp.Bridges.NewsConsumer

  def recent(conn, params) do
    n =
      case Integer.parse(Map.get(params, "limit", "50")) do
        {n, _} when n > 0 and n <= 200 -> n
        _ -> 50
      end

    json(conn, %{items: NewsConsumer.recent(n)})
  end
end
