# ADR 0004 — SQLite for OLTP, DuckDB for OLAP

Date: 2026-04-29
Status: Accepted

## Context

We need persistence for two distinct workloads:
- **Transactional** (OLTP): orders, positions, trades, audit log. Concurrent reads/writes, small rows, ACID.
- **Analytical** (OLAP): historical klines, features, backtest results. Large scans, columnar.

## Decision

- SQLite (via Ecto in Phoenix; via SQLAlchemy/aiosqlite in Python) for OLTP.
- DuckDB (Python only) for OLAP.

## Rationale

- **SQLite** is the simplest reliable embedded DB. Single file, ACID, no separate process. Phoenix has excellent integration via `ecto_sqlite3`. For our scale (single-user, hundreds of orders/day), it's overkill in capacity and perfect in simplicity.
- **DuckDB** has become the de-facto local analytics engine in 2025. Columnar storage, vectorized execution, parquet integration, and zero ops. Outperforms TimescaleDB for our access patterns (batch feature extraction, backtest scans).
- Splitting OLTP and OLAP avoids the worst-case where a long analytical query blocks order persistence.

## Consequences

Positive: zero infra ops, fast development, excellent local performance.

Negative: SQLite single-writer limitations require us to coordinate writes between Phoenix and Python (mitigated by table-level separation: Phoenix owns schema migrations and writes to `audit_log`/`approvals`; Python writes to `orders`/`trades`/`fills`).

Future: if we ever scale beyond local (a separate repo/project), revisit with PostgreSQL + TimescaleDB.
