defmodule PhoenixApp.Repo.Migrations.CreateStrategies do
  use Ecto.Migration

  def change do
    create table(:strategies) do
      add :name, :string, null: false
      add :enabled, :boolean, default: false, null: false
      add :symbols, {:array, :string}, default: []
      add :timeframe, :string
      add :params, :map, default: %{}

      timestamps(type: :utc_datetime_usec)
    end

    create unique_index(:strategies, [:name])
  end
end
