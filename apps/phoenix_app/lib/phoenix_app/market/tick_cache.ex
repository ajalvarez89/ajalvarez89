defmodule PhoenixApp.Market.TickCache do
  @moduledoc """
  In-memory cache (ETS) of the latest tick per symbol.
  Read by channels and HTTP controllers; written by the Redis Streams consumer.
  """
  use GenServer

  @table :market_ticks

  def start_link(_opts), do: GenServer.start_link(__MODULE__, nil, name: __MODULE__)

  @doc "Returns the latest tick for `symbol`, or `nil`."
  def get(symbol) when is_binary(symbol) do
    case :ets.lookup(@table, symbol) do
      [{^symbol, tick}] -> tick
      [] -> nil
    end
  end

  @doc "Stores `tick` for `symbol`."
  def put(symbol, %{} = tick) when is_binary(symbol) do
    :ets.insert(@table, {symbol, tick})
    :ok
  end

  @impl true
  def init(_) do
    :ets.new(@table, [:set, :public, :named_table, read_concurrency: true])
    {:ok, %{}}
  end
end
