defmodule PhoenixAppWeb.NewsChannel do
  @moduledoc """
  Live news feed.
  Topic: "news:lobby". Receives `:news` events broadcast by NewsConsumer.
  """
  use Phoenix.Channel

  alias Phoenix.PubSub
  alias PhoenixApp.Bridges.NewsConsumer

  @pubsub PhoenixApp.PubSub

  @impl true
  def join("news:lobby", _payload, socket) do
    PubSub.subscribe(@pubsub, "news:lobby")
    send(self(), :replay_buffer)
    {:ok, %{}, socket}
  end

  @impl true
  def handle_info(:replay_buffer, socket) do
    items = NewsConsumer.recent(20)
    push(socket, "snapshot", %{items: items})
    {:noreply, socket}
  end

  @impl true
  def handle_info({:news, item}, socket) do
    push(socket, "item", item)
    {:noreply, socket}
  end
end
