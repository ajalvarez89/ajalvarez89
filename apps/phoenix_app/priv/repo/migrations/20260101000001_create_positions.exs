defmodule PhoenixApp.Repo.Migrations.CreatePositions do
  use Ecto.Migration

  def change do
    create table(:positions) do
      add :symbol, :string, null: false
      add :side, :string, null: false
      add :quantity, :decimal, precision: 20, scale: 8, null: false
      add :avg_entry_price, :decimal, precision: 20, scale: 8, null: false
      add :unrealized_pnl, :decimal, precision: 20, scale: 8, default: 0
      add :realized_pnl, :decimal, precision: 20, scale: 8, default: 0
      add :strategy, :string
      add :mode, :string, null: false
      add :opened_at, :utc_datetime_usec, null: false
      add :closed_at, :utc_datetime_usec

      timestamps(type: :utc_datetime_usec)
    end

    create index(:positions, [:symbol])
    create index(:positions, [:strategy])
    create index(:positions, [:closed_at])
  end
end
