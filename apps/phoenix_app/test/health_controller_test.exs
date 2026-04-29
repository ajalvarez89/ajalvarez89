defmodule PhoenixAppWeb.HealthControllerTest do
  use ExUnit.Case, async: true
  use Phoenix.ConnTest
  @endpoint PhoenixAppWeb.Endpoint

  test "GET /health returns ok" do
    conn = build_conn() |> get("/health")
    assert json_response(conn, 200)["status"] == "ok"
    assert json_response(conn, 200)["service"] == "phoenix_app"
  end
end
