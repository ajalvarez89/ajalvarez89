defmodule PhoenixApp.Repo.Migrations.CreateOrders do
  use Ecto.Migration

  def change do
    create table(:orders) do
      add :external_id, :string
      add :symbol, :string, null: false
      add :side, :string, null: false
      add :type, :string, null: false
      add :status, :string, null: false
      add :quantity, :decimal, precision: 20, scale: 8
      add :price, :decimal, precision: 20, scale: 8
      add :stop_loss, :decimal, precision: 20, scale: 8
      add :take_profit, :decimal, precision: 20, scale: 8
      add :strategy, :string
      add :mode, :string, null: false
      add :payload, :map

      timestamps(type: :utc_datetime_usec)
    end

    create index(:orders, [:symbol])
    create index(:orders, [:status])
    create index(:orders, [:strategy])
    create unique_index(:orders, [:external_id], where: "external_id IS NOT NULL")
  end
end
