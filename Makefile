SHELL := /bin/bash
.DEFAULT_GOAL := help

ENV_FILE := .env
COMPOSE := docker compose
COMPOSE_TESTNET := docker compose -f docker-compose.yml -f docker-compose.testnet.yml
COMPOSE_PROD := docker compose -f docker-compose.yml -f docker-compose.prod.yml

# ============================================================================
# Help
# ============================================================================
.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make <target>\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# ============================================================================
# Setup
# ============================================================================
.PHONY: env
env: ## Create .env from template if missing
	@if [ ! -f $(ENV_FILE) ]; then cp .env.example $(ENV_FILE) && chmod 600 $(ENV_FILE) && echo "Created $(ENV_FILE) — edit it and re-run"; else echo "$(ENV_FILE) already exists"; fi

.PHONY: preflight
preflight: ## Run preflight checks (API keys, connectivity, balance)
	@bash scripts/preflight.sh

# ============================================================================
# Docker lifecycle
# ============================================================================
.PHONY: up
up: ## Start all services in testnet mode (default)
	$(COMPOSE_TESTNET) up -d --build

.PHONY: up-paper
up-paper: ## Start all services in paper-trading mode
	TRADING_MODE=paper $(COMPOSE) up -d --build

.PHONY: up-live
up-live: ## Start all services in LIVE mode (REAL MONEY) — requires manual confirmation
	@bash scripts/enable_live.sh && $(COMPOSE_PROD) up -d --build

.PHONY: down
down: ## Stop all services
	$(COMPOSE) down

.PHONY: restart
restart: down up ## Restart all services in testnet mode

.PHONY: ps
ps: ## List running services
	$(COMPOSE) ps

.PHONY: logs
logs: ## Tail logs from all services
	$(COMPOSE) logs -f --tail=200

.PHONY: logs-trading
logs-trading: ## Tail trading_engine logs
	$(COMPOSE) logs -f --tail=200 trading_engine

.PHONY: logs-ml
logs-ml: ## Tail ml_service logs
	$(COMPOSE) logs -f --tail=200 ml_service

.PHONY: logs-phoenix
logs-phoenix: ## Tail phoenix_app logs
	$(COMPOSE) logs -f --tail=200 phoenix_app

# ============================================================================
# Operations
# ============================================================================
.PHONY: approve
approve: ## Authorize order execution for the next 24h
	@curl -fsS -X POST http://localhost:4000/api/admin/approve -H "Content-Type: application/json" -d '{"actor":"user","ttl_hours":24}' && echo

.PHONY: kill
kill: ## KILL SWITCH: cancel orders and close positions
	@bash scripts/kill_switch.sh

.PHONY: resume
resume: ## Resume trading after kill switch
	@curl -fsS -X POST http://localhost:8001/admin/resume && echo

.PHONY: status
status: ## Show health status of all services
	@echo "Phoenix:        $$(curl -sf -o /dev/null -w '%{http_code}' http://localhost:4000/health || echo DOWN)"
	@echo "Trading engine: $$(curl -sf -o /dev/null -w '%{http_code}' http://localhost:8001/health || echo DOWN)"
	@echo "ML service:     $$(curl -sf -o /dev/null -w '%{http_code}' http://localhost:8002/health || echo DOWN)"
	@echo "News collector: $$(curl -sf -o /dev/null -w '%{http_code}' http://localhost:8003/health || echo DOWN)"
	@echo "Web:            $$(curl -sf -o /dev/null -w '%{http_code}' http://localhost:3000 || echo DOWN)"

# ============================================================================
# Data / ML
# ============================================================================
.PHONY: seed
seed: ## Seed historical klines into DuckDB (runs inside ml_service container)
	$(COMPOSE) exec ml_service python /app/scripts/seed_historical.py

.PHONY: train
train: ## Train baseline direction classifier (HistGradientBoosting) and promote
	$(COMPOSE) exec ml_service python -m ml_service.training.train_baseline --promote

.PHONY: backtest
backtest: ## Run a backtest with the active strategy across configured pairs
	$(COMPOSE) exec ml_service python /app/scripts/backtest_run.py

# ============================================================================
# Tests
# ============================================================================
.PHONY: test
test: test-phoenix test-trading test-ml test-web ## Run all tests

.PHONY: test-phoenix
test-phoenix: ## Run Phoenix tests
	$(COMPOSE) exec phoenix_app mix test

.PHONY: test-trading
test-trading: ## Run trading_engine tests
	$(COMPOSE) exec trading_engine pytest

.PHONY: test-ml
test-ml: ## Run ml_service tests
	$(COMPOSE) exec ml_service pytest

.PHONY: test-web
test-web: ## Run web tests
	$(COMPOSE) exec web pnpm test

# ============================================================================
# Cleanup
# ============================================================================
.PHONY: clean
clean: ## Remove containers, volumes, and build artifacts
	$(COMPOSE) down -v
	rm -rf data/sqlite/*.sqlite data/duckdb/*.duckdb
	@echo "Cleaned. Local model weights NOT removed; delete apps/ml_service/models/ manually if needed."
