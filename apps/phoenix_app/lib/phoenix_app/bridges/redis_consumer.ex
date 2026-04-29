defmodule PhoenixApp.Bridges.RedisConsumer do
  @moduledoc """
  Consumes Redis Streams populated by `trading_engine` and broadcasts events
  through Phoenix.PubSub to the appropriate channels.

  Streams handled in Phase 1:
    - `market.klines` -> "market:<SYMBOL>" with event "kline"
    - `market.ticks`  -> "market:<SYMBOL>" with event "tick" (also caches latest)

  Implementation note: we use blocking `XREAD` from a single consumer (no group)
  in Phase 1 since this is a single-instance local deployment. Phase 4+ will
  switch to consumer groups if we add HA.
  """
  use GenServer

  require Logger

  alias PhoenixApp.Market.TickCache
  alias Phoenix.PubSub

  @streams ["market.klines", "market.ticks"]
  @block_ms 5_000
  @initial_id "$"
  @reconnect_backoff_ms 2_000

  @pubsub PhoenixApp.PubSub

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: Keyword.get(opts, :name, __MODULE__))
  end

  @impl true
  def init(_opts) do
    state = %{ids: Map.new(@streams, fn s -> {s, @initial_id} end)}
    send(self(), :read)
    {:ok, state}
  end

  @impl true
  def handle_info(:read, state) do
    streams = @streams
    ids = Enum.map(streams, &Map.fetch!(state.ids, &1))

    case Redix.command(:redix, ["XREAD", "BLOCK", @block_ms, "STREAMS"] ++ streams ++ ids) do
      {:ok, nil} ->
        # Block window expired without messages — keep reading.
        send(self(), :read)
        {:noreply, state}

      {:ok, results} when is_list(results) ->
        new_state = Enum.reduce(results, state, &process_stream/2)
        send(self(), :read)
        {:noreply, new_state}

      {:error, reason} ->
        Logger.warning("redis_consumer.error: #{inspect(reason)}")
        Process.send_after(self(), :read, @reconnect_backoff_ms)
        {:noreply, state}
    end
  end

  defp process_stream([stream_name, entries], state) do
    {last_id, _} =
      Enum.reduce(entries, {Map.get(state.ids, stream_name), nil}, fn [id, fields], {_acc_id, _acc} ->
        handle_entry(stream_name, fields)
        {id, nil}
      end)

    %{state | ids: Map.put(state.ids, stream_name, last_id)}
  end

  defp handle_entry("market.klines", fields) do
    fields
    |> kv_to_map()
    |> Map.get("data")
    |> decode_payload()
    |> case do
      {:ok, %{"symbol" => sym} = payload} ->
        PubSub.broadcast(@pubsub, "market:#{sym}", {:kline, payload})

      _ ->
        :noop
    end
  end

  defp handle_entry("market.ticks", fields) do
    fields
    |> kv_to_map()
    |> Map.get("data")
    |> decode_payload()
    |> case do
      {:ok, %{"symbol" => sym} = payload} ->
        TickCache.put(sym, payload)
        PubSub.broadcast(@pubsub, "market:#{sym}", {:tick, payload})

      _ ->
        :noop
    end
  end

  defp kv_to_map(list) when is_list(list) do
    list
    |> Enum.chunk_every(2)
    |> Enum.into(%{}, fn [k, v] -> {k, v} end)
  end

  defp decode_payload(nil), do: :error
  defp decode_payload(json) when is_binary(json) do
    case Jason.decode(json) do
      {:ok, map} -> {:ok, map}
      _ -> :error
    end
  end
end
