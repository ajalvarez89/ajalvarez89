# ADR 0001 — Phoenix-centric híbrido architecture

Date: 2026-04-29
Status: Accepted

## Context

We need to build a local crypto trading bot with:
- Real-time market data ingestion and dashboard updates.
- ML/AI forecasting and sentiment analysis.
- Hard isolation between the component that holds Binance API keys and the rest.
- Dashboard with live P&L, charts, and kill switch.

Candidate stacks: pure Python (Freqtrade), pure Next.js, or híbrido.

## Decision

Phoenix/Elixir as the gateway and real-time backbone, with Python microservices for trading execution and ML, and Next.js for the dashboard.

## Rationale

- **Phoenix Channels** provide best-in-class WebSocket fan-out (BEAM concurrency). Far simpler than wiring Socket.io or SSE in Node.
- **Python** is the de-facto stack for ML (NeuralForecast, FinBERT, VectorBT) and has the most mature Binance client (`python-binance`).
- **Next.js** is the user's preferred frontend; TradingView Lightweight Charts integrates cleanly.
- Strict isolation: keys in `trading_engine` only; everything else on need-to-know.
- Pure-Python alternatives (Freqtrade) bundle a dashboard but lack the real-time WS fan-out and architectural separation we want.

## Consequences

Positive:
- Best component for each concern.
- Phoenix supervises long-running connections gracefully (BEAM restart trees).
- Clear contract boundaries via JSON Schemas.

Negative:
- Three runtimes to operate (Erlang BEAM + Python + Node).
- Slightly more setup overhead than a single-language stack.
- More inter-service serialization.

Mitigations: Docker Compose orchestrates all three; JSON Schemas (`/contracts`) prevent contract drift; Makefile abstracts daily commands.
