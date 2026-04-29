# ADR 0003 — Redis Streams over RabbitMQ/Kafka for inter-service eventing

Date: 2026-04-29
Status: Accepted

## Context

Services need pub/sub for ticks, signals, news, and order events. Options: Redis Streams, RabbitMQ, NATS, Kafka.

## Decision

Redis Streams.

## Rationale

- **Already running Redis** for caching and ephemeral state. No additional infrastructure.
- Streams give us at-least-once delivery, consumer groups, and persistence sufficient for retention windows we care about (minutes to hours).
- Clients exist in all three languages (`redix` for Elixir, `redis-py` for Python, `ioredis` for Node — though we don't push events from Node).
- Local-only deployment doesn't need the throughput of Kafka or the routing flexibility of RabbitMQ.

## Consequences

Positive: simpler ops, fewer dependencies.

Negative: not suitable for very long retention or cross-region replication. We accept this — the system is local-only by design.
