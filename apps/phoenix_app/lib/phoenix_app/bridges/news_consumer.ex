defmodule PhoenixApp.Bridges.NewsConsumer do
  @moduledoc """
  Consumes the `news.scored` Redis Stream and broadcasts items via PubSub
  on the topic "news:lobby". Also keeps a small in-memory buffer of the
  last N items for the dashboard's initial paint.
  """
  use GenServer

  require Logger
  alias Phoenix.PubSub

  @stream "news.scored"
  @block_ms 5_000
  @buffer_max 100
  @pubsub PhoenixApp.PubSub

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: Keyword.get(opts, :name, __MODULE__))
  end

  @doc "Returns up to N most-recent scored news items (memory buffer)."
  def recent(n \\ 50) do
    GenServer.call(__MODULE__, {:recent, n})
  end

  @impl true
  def init(_opts) do
    state = %{last_id: "$", buffer: :queue.new()}
    send(self(), :read)
    {:ok, state}
  end

  @impl true
  def handle_call({:recent, n}, _from, state) do
    items = state.buffer |> :queue.to_list() |> Enum.reverse() |> Enum.take(n)
    {:reply, items, state}
  end

  @impl true
  def handle_info(:read, %{last_id: last_id, buffer: buffer} = state) do
    case Redix.command(:redix, ["XREAD", "BLOCK", @block_ms, "STREAMS", @stream, last_id]) do
      {:ok, nil} ->
        send(self(), :read)
        {:noreply, state}

      {:ok, [[@stream, entries]]} ->
        {new_last, new_buffer} =
          Enum.reduce(entries, {last_id, buffer}, fn [id, fields], {_l, b} ->
            payload = decode(fields)
            if payload, do: PubSub.broadcast(@pubsub, "news:lobby", {:news, payload})
            updated = if payload, do: enqueue(b, payload), else: b
            {id, updated}
          end)

        send(self(), :read)
        {:noreply, %{state | last_id: new_last, buffer: new_buffer}}

      {:error, reason} ->
        Logger.warning("news_consumer.error: #{inspect(reason)}")
        Process.send_after(self(), :read, 2_000)
        {:noreply, state}
    end
  end

  defp enqueue(q, item) do
    q = :queue.in(item, q)
    if :queue.len(q) > @buffer_max do
      {_, q} = :queue.out(q)
      q
    else
      q
    end
  end

  defp decode(fields) when is_list(fields) do
    case fields |> Enum.chunk_every(2) |> Enum.into(%{}, fn [k, v] -> {k, v} end) do
      %{"data" => data} ->
        case Jason.decode(data) do
          {:ok, m} -> m
          _ -> nil
        end

      _ ->
        nil
    end
  end
end
