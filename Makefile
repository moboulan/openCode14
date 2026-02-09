# ============================================================
# Incident Platform — Root Makefile
# Orchestrates all services via Docker Compose
# ============================================================

COMPOSE       := docker compose
SERVICES      := alert-ingestion
DB_CONTAINER  := incident-db

.PHONY: all build up down restart logs ps \
        db-shell db-reset \
        lint test ci \
        clean help

# ── Default ──────────────────────────────────────────────────

all: build up  ## Build and start all services

# ── Docker Compose ───────────────────────────────────────────

build:  ## Build all Docker images
	$(COMPOSE) build

up:  ## Start all services (detached)
	$(COMPOSE) up -d
	@echo "Waiting for database to be healthy…"
	@until docker inspect --format='{{.State.Health.Status}}' $(DB_CONTAINER) 2>/dev/null | grep -q healthy; do \
		sleep 2; \
	done
	@echo "✅ Database is healthy"
	@echo "Services:"
	@echo "  Alert Ingestion  → http://localhost:8001"
	@echo "  Database         → localhost:5432"

down:  ## Stop and remove all containers
	$(COMPOSE) down

down-v:  ## Stop, remove containers AND volumes (full reset)
	$(COMPOSE) down -v --remove-orphans

restart: down up  ## Restart all services

logs:  ## Tail logs from all services
	$(COMPOSE) logs -f

logs-%:  ## Tail logs for a specific service (e.g. make logs-alert-ingestion)
	$(COMPOSE) logs -f $*

ps:  ## Show running containers
	$(COMPOSE) ps

# ── Database ─────────────────────────────────────────────────

db-shell:  ## Open a psql shell in the database container
	docker exec -it $(DB_CONTAINER) psql -U postgres -d incident_platform

db-reset: down-v up  ## Destroy DB volume and reinitialise from scratch

# ── Per-service CI (delegates to service Makefiles) ──────────

lint:  ## Run linters for alert-ingestion-service
	$(MAKE) -C alert-ingestion-service lint

test:  ## Run tests for alert-ingestion-service
	$(MAKE) -C alert-ingestion-service test

ci:  ## Run full local CI (lint + test) for alert-ingestion-service
	$(MAKE) -C alert-ingestion-service all

coverage:  ## Run tests with coverage and open HTML report
	$(MAKE) -C alert-ingestion-service test
	@echo "Opening coverage report…"
	@xdg-open alert-ingestion-service/htmlcov/index.html 2>/dev/null || open alert-ingestion-service/htmlcov/index.html 2>/dev/null || echo "Report at alert-ingestion-service/htmlcov/index.html"

# ── Health & Smoke ───────────────────────────────────────────

health:  ## Hit health endpoints
	@echo "── Alert Ingestion ──"
	@curl -sf http://localhost:8001/health | python3 -m json.tool
	@curl -sf http://localhost:8001/health/ready | python3 -m json.tool
	@curl -sf http://localhost:8001/health/live  | python3 -m json.tool

smoke:  ## Quick smoke test (POST + GET alert)
	@echo "── POST alert ──"
	@curl -sf -X POST http://localhost:8001/api/v1/alerts \
		-H "Content-Type: application/json" \
		-d '{"service":"make-smoke","severity":"low","message":"root Makefile smoke test"}' | python3 -m json.tool
	@echo "── GET alerts ──"
	@curl -sf "http://localhost:8001/api/v1/alerts?service=make-smoke" | python3 -m json.tool

# ── Cleanup ──────────────────────────────────────────────────

clean:  ## Remove build artifacts across all services
	$(MAKE) -C alert-ingestion-service clean
	docker image prune -f

# ── Help ─────────────────────────────────────────────────────

help:  ## Show this help
	@grep -E '^[a-zA-Z_%-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
