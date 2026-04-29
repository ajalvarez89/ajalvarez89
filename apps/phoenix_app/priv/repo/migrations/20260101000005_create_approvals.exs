defmodule PhoenixApp.Repo.Migrations.CreateApprovals do
  use Ecto.Migration

  def change do
    create table(:approvals) do
      add :actor, :string, null: false
      add :action, :string, null: false, default: "orders_approved"
      add :granted_at, :utc_datetime_usec, null: false
      add :expires_at, :utc_datetime_usec, null: false
      add :revoked, :boolean, default: false

      timestamps(type: :utc_datetime_usec)
    end

    create index(:approvals, [:expires_at])
    create index(:approvals, [:action, :revoked])
  end
end
