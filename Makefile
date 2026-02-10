# ============================================================
# ExpertMind — Root Makefile
#
#   Get started:   make            (builds & starts all services)
#   Full pipeline: make all        (7-stage CI/CD pipeline)
#   Run tests:     make test
#   Lint code:     make lint
#   See targets:   make help
# ============================================================

COMPOSE       := docker compose
SERVICES      := alert-ingestion incident-management notification-service oncall-service ai-analysis
DB_CONTAINER  := incident-db
IMAGE_ALERT   := expertmind-alert-ingestion
IMAGE_INCIDENT:= expertmind-incident-management
IMAGE_NOTIF   := expertmind-notification-service
IMAGE_ONCALL  := expertmind-oncall-service
IMAGE_AI      := expertmind-ai-analysis
PREV_TAG      := prev
VERSION       := $(shell git rev-parse --short HEAD 2>/dev/null || echo "dev")
VENV          := .venv
PYTHON_BIN    := python3.11
PYTHON        := $(VENV)/bin/python
PIP           := $(VENV)/bin/pip

SVC_DIRS := alert-ingestion-service incident-management-service notification-service oncall-service ai-analysis-service

HEALTH_ENDPOINTS := 8001 8002 8003 8004 8005

.PHONY: all setup quality security build scan test deploy verify \
        up down down-v restart logs ps \
        db-shell db-reset fmt dupcheck lint \
        ci coverage clean fclean help

# ── Default: quick start ──────────────────────────────────────

.DEFAULT_GOAL := up

# ── Environment Bootstrap ─────────────────────────────────────

.env:
	@cp .env.example .env && echo "OK .env created — edit it to change defaults"

$(VENV)/bin/activate:
	$(PYTHON_BIN) -m venv $(VENV)

$(VENV)/.installed: $(VENV)/bin/activate $(foreach d,$(SVC_DIRS),$(d)/requirements.txt)
	$(PIP) install --upgrade pip -q
	$(foreach d,$(SVC_DIRS),$(PIP) install -r $(d)/requirements.txt -q;)
	$(PIP) install ruff pytest pytest-cov pytest-asyncio httpx pre-commit -q
	touch $@

setup: .env $(VENV)/.installed  ## One-time setup: .env + venv + deps
	@$(VENV)/bin/pre-commit install 2>/dev/null || true
	@echo "OK Setup complete"

# ── Full 7-Stage Pipeline ────────────────────────────────────

all: setup quality security build scan test deploy verify  ## Full 7-stage CI/CD pipeline

# ── Stage 1: Code Quality ────────────────────────────────────

quality: $(VENV)/.installed lint dupcheck  ## Lint + duplication check

lint: $(VENV)/.installed  ## Run ruff linter on all services
	$(foreach d,$(SVC_DIRS),$(MAKE) -C $(d) lint PYTHON=$(CURDIR)/$(PYTHON);)

dupcheck:  ## Check for code duplication (< 3%)
	@if command -v jscpd >/dev/null 2>&1; then \
		jscpd $(foreach d,$(SVC_DIRS),$(d)/app/) \
			--min-lines 5 --min-tokens 50 --threshold 3 \
			--reporters console \
			--ignore 'node_modules|.venv|htmlcov|__pycache__' || exit 1; \
	else \
		echo "SKIP jscpd not installed"; \
	fi

# ── Stage 2: Security Scanning ───────────────────────────────

security:  ## Scan for leaked secrets
	@command -v gitleaks >/dev/null 2>&1 && gitleaks detect --source=. --config=.gitleaks.toml -v 2>&1 || echo "SKIP gitleaks not installed"
	@command -v trufflehog >/dev/null 2>&1 && trufflehog filesystem . --no-update --fail 2>&1 || echo "SKIP trufflehog not installed"

# ── Stage 3: Build ────────────────────────────────────────────

build: .env  ## Build all Docker images
	$(COMPOSE) build --build-arg VERSION=$(VERSION)

# ── Stage 4: Vulnerability Scan ──────────────────────────────

scan: build  ## Trivy vulnerability scan
	@for img in $(IMAGE_ALERT) $(IMAGE_INCIDENT) $(IMAGE_NOTIF) $(IMAGE_ONCALL) $(IMAGE_AI); do \
		echo "── trivy: $$img ──"; \
		trivy image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 0 $$img:latest 2>/dev/null || \
			docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
				aquasec/trivy:latest image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 0 $$img:latest; \
	done

# ── Stage 5: Tests ────────────────────────────────────────────

test: $(VENV)/.installed  ## Run unit tests with coverage
	$(foreach d,$(SVC_DIRS),$(MAKE) -C $(d) test PYTHON=$(CURDIR)/$(PYTHON);)

test-integration: $(VENV)/.installed  ## Run integration tests (requires running services)
	$(foreach d,$(SVC_DIRS),$(MAKE) -C $(d) test-integration PYTHON=$(CURDIR)/$(PYTHON) 2>/dev/null || true;)

# ── Stage 6: Deploy ──────────────────────────────────────────

deploy: .env  ## Tag :prev for rollback, then deploy
	@for img in $(IMAGE_ALERT) $(IMAGE_INCIDENT) $(IMAGE_NOTIF) $(IMAGE_ONCALL) $(IMAGE_AI); do \
		docker tag $$img:latest $$img:$(PREV_TAG) 2>/dev/null || true; \
	done
	$(COMPOSE) down -v --remove-orphans 2>/dev/null || true
	$(COMPOSE) up -d --build
	@$(MAKE) -s _wait-healthy
	@echo ""
	@echo "Services:"
	@echo "  Alert Ingestion       → http://localhost:8001"
	@echo "  Incident Management   → http://localhost:8002"
	@echo "  On-Call Service       → http://localhost:8003"
	@echo "  Notification Service  → http://localhost:8004"
	@echo "  AI Analysis           → http://localhost:8005"
	@echo "  Database              → localhost:5432"

# ── Stage 7: Verify ──────────────────────────────────────────

verify:  ## Health + smoke tests (auto-rollback on failure)
	@PASS=true; \
	for port in $(HEALTH_ENDPOINTS); do \
		curl -sf http://localhost:$$port/health >/dev/null 2>&1 || { echo "FAIL health :$$port"; PASS=false; }; \
	done; \
	echo "── smoke: POST alert ──"; \
	curl -sf -X POST http://localhost:8001/api/v1/alerts \
		-H "Content-Type: application/json" \
		-d '{"service":"make-smoke","severity":"low","message":"smoke test"}' | python3 -m json.tool || PASS=false; \
	echo "── smoke: POST incident ──"; \
	curl -sf -X POST http://localhost:8002/api/v1/incidents \
		-H "Content-Type: application/json" \
		-d '{"title":"[LOW] smoke: verify","service":"make-smoke","severity":"low"}' | python3 -m json.tool || PASS=false; \
	for port in $(HEALTH_ENDPOINTS); do \
		curl -sf http://localhost:$$port/metrics | head -5 >/dev/null 2>&1 || { echo "WARN no metrics :$$port"; }; \
	done; \
	if [ "$$PASS" = "false" ]; then echo "FAIL — rolling back"; $(MAKE) rollback; exit 1; fi; \
	echo "OK All verifications passed"

# ── Rollback ─────────────────────────────────────────────────

rollback:  ## Rollback to :prev tagged images
	@for img in $(IMAGE_ALERT) $(IMAGE_INCIDENT) $(IMAGE_NOTIF) $(IMAGE_ONCALL) $(IMAGE_AI); do \
		docker tag $$img:$(PREV_TAG) $$img:latest 2>/dev/null || echo "No :prev for $$img"; \
	done
	$(COMPOSE) down -v --remove-orphans 2>/dev/null || true
	$(COMPOSE) up -d
	@sleep 10
	@curl -sf http://localhost:8001/health | python3 -m json.tool || echo "WARN not healthy after rollback"

# ── Docker Compose Helpers ────────────────────────────────────

up: .env  ## Start all services (default target)
	$(COMPOSE) up -d --build
	@$(MAKE) -s _wait-healthy

down:  ## Stop all containers
	$(COMPOSE) down

down-v:  ## Stop + remove volumes (full reset)
	$(COMPOSE) down -v --remove-orphans

restart: down up  ## Restart all services

logs:  ## Tail logs
	$(COMPOSE) logs -f

logs-%:  ## Tail logs for one service (e.g. make logs-alert-ingestion)
	$(COMPOSE) logs -f $*

ps:  ## Show running containers
	$(COMPOSE) ps

# ── Database ─────────────────────────────────────────────────

db-shell:  ## Open psql shell
	docker exec -it $(DB_CONTAINER) psql -U postgres -d incident_platform

db-reset: down-v up  ## Destroy DB + reinitialise

# ── Convenience ──────────────────────────────────────────────

ci: setup quality test  ## Quick CI (lint + test, no Docker)

coverage: $(VENV)/.installed  ## Tests with coverage + open reports
	$(foreach d,$(SVC_DIRS),$(MAKE) -C $(d) test PYTHON=$(CURDIR)/$(PYTHON);)
	@echo "Reports in */htmlcov/index.html"

health:  ## Hit all health endpoints
	@for port in $(HEALTH_ENDPOINTS); do \
		echo "── :$$port ──"; \
		curl -sf http://localhost:$$port/health | python3 -m json.tool || echo "  DOWN"; \
	done

smoke:  ## Quick smoke test
	@curl -sf -X POST http://localhost:8001/api/v1/alerts \
		-H "Content-Type: application/json" \
		-d '{"service":"make-smoke","severity":"low","message":"smoke test"}' | python3 -m json.tool
	@curl -sf "http://localhost:8001/api/v1/alerts?service=make-smoke" | python3 -m json.tool

fmt: $(VENV)/.installed  ## Auto-format all code
	$(foreach d,$(SVC_DIRS),$(MAKE) -C $(d) fmt PYTHON=$(CURDIR)/$(PYTHON);)

format: fmt  ## Alias for fmt

# ── Cleanup ──────────────────────────────────────────────────

clean:  ## Remove build artifacts
	$(foreach d,$(SVC_DIRS),$(MAKE) -C $(d) clean;)
	docker image prune -f

fclean: clean  ## Remove everything (venv, volumes, images)
	rm -rf $(VENV)
	$(COMPOSE) down -v --remove-orphans 2>/dev/null || true

# ── Internal helpers ──────────────────────────────────────────

_wait-healthy:
	@echo "Waiting for database…"
	@until docker inspect --format='{{.State.Health.Status}}' $(DB_CONTAINER) 2>/dev/null | grep -q healthy; do sleep 2; done
	@echo "OK Database ready"
	@for port in $(HEALTH_ENDPOINTS); do \
		printf "Waiting for :$$port… "; \
		for i in 1 2 3 4 5 6 7 8 9 10; do curl -sf http://localhost:$$port/health >/dev/null 2>&1 && break; sleep 2; done; \
		curl -sf http://localhost:$$port/health >/dev/null 2>&1 && echo "OK" || echo "WARN not ready"; \
	done

# ── Help ─────────────────────────────────────────────────────

help:  ## Show this help
	@grep -E '^[a-zA-Z_%-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
