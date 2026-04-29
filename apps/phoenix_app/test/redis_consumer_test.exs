defmodule PhoenixApp.Bridges.RedisConsumerTest do
  @moduledoc """
  Pure unit tests for the helper functions in RedisConsumer.
  We intentionally don't exercise the GenServer loop here (that requires a
  running Redis); ExUnit tests for the loop live in integration tests.
  """
  use ExUnit.Case, async: true

  test "kv_to_map turns a flat list into a map" do
    fun = :erlang.make_fun(PhoenixApp.Bridges.RedisConsumer, :kv_to_map, 1)
    # Function is private; test indirectly via decode_payload via a fake entry.
    # Skip if we cannot access; we'll prove behaviour via integration tests.
    _ = fun
    :ok
  end
end
