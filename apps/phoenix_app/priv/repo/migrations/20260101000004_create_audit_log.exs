defmodule PhoenixApp.Repo.Migrations.CreateAuditLog do
  use Ecto.Migration

  def change do
    create table(:audit_log) do
      add :ts, :utc_datetime_usec, null: false
      add :actor, :string, null: false
      add :action, :string, null: false
      add :payload, :map, default: %{}
      add :signature_hash, :string

      timestamps(type: :utc_datetime_usec, updated_at: false)
    end

    create index(:audit_log, [:ts])
    create index(:audit_log, [:actor])
    create index(:audit_log, [:action])
  end
end
