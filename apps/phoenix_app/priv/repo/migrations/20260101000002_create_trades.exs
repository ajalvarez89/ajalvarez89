defmodule PhoenixApp.Repo.Migrations.CreateTrades do
  use Ecto.Migration

  def change do
    create table(:trades) do
      add :order_id, references(:orders, on_delete: :nilify_all)
      add :position_id, references(:positions, on_delete: :nilify_all)
      add :symbol, :string, null: false
      add :side, :string, null: false
      add :quantity, :decimal, precision: 20, scale: 8, null: false
      add :price, :decimal, precision: 20, scale: 8, null: false
      add :fee, :decimal, precision: 20, scale: 8, default: 0
      add :fee_asset, :string
      add :realized_pnl, :decimal, precision: 20, scale: 8
      add :mode, :string, null: false
      add :executed_at, :utc_datetime_usec, null: false

      timestamps(type: :utc_datetime_usec)
    end

    create index(:trades, [:symbol])
    create index(:trades, [:executed_at])
  end
end
