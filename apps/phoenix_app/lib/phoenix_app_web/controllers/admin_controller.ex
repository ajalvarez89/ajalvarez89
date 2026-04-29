defmodule PhoenixAppWeb.AdminController do
  @moduledoc """
  Stubs for administrative actions: approve orders, kill switch, resume.
  Real persistence/forwarding to trading_engine is wired up in Fase 2.
  """
  use Phoenix.Controller, formats: [:json]

  def approve(conn, params) do
    actor = Map.get(params, "actor", "user")
    ttl_hours = Map.get(params, "ttl_hours", 24)

    json(conn, %{
      status: "ok",
      action: "approve",
      actor: actor,
      ttl_hours: ttl_hours,
      note: "Stub for Fase 0; real flag persistence lands in Fase 2"
    })
  end

  def kill(conn, _params) do
    json(conn, %{status: "ok", action: "kill", note: "Stub — wires to trading_engine in Fase 2"})
  end

  def resume(conn, _params) do
    json(conn, %{status: "ok", action: "resume", note: "Stub — wires to trading_engine in Fase 2"})
  end
end
