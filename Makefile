# ============================================================
# Incident Platform — Root Makefile
# 7-stage local CI/CD pipeline (no GitHub Actions needed)
#
#   Fresh clone:   make setup && make all
#   Quick start:   make up
#   Full pipeline: make all
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

.PHONY: all setup quality security build scan test deploy verify \
        up down down-v restart logs ps \
        db-shell db-reset fmt dupcheck \
        ci coverage clean help

# ── Environment Bootstrap ─────────────────────────────────────

.env:  ## Auto-create .env from .env.example on first run
	@echo "── creating .env from .env.example ──"
	cp .env.example .env
	@echo "OK .env created -- edit it to change defaults"

$(VENV)/bin/activate:
	$(PYTHON_BIN) -m venv $(VENV)

$(VENV)/.installed: $(VENV)/bin/activate alert-ingestion-service/requirements.txt incident-management-service/requirements.txt notification-service/requirements.txt oncall-service/requirements.txt ai-analysis-service/requirements.txt
	$(PIP) install --upgrade pip -q
	$(PIP) install -r alert-ingestion-service/requirements.txt -q
	$(PIP) install -r incident-management-service/requirements.txt -q
	$(PIP) install -r notification-service/requirements.txt -q
	$(PIP) install -r oncall-service/requirements.txt -q
	$(PIP) install -r ai-analysis-service/requirements.txt -q
	$(PIP) install flake8 pylint black isort autoflake pytest pytest-cov pytest-asyncio httpx pre-commit -q
	touch $(VENV)/.installed

setup: .env $(VENV)/.installed  ## One-time setup: create .env + venv + install deps
	@$(VENV)/bin/pre-commit install 2>/dev/null || true
	@echo "OK Setup complete -- venv at $(VENV), .env ready, pre-commit hooks installed"

# ── Full 7-Stage Pipeline ────────────────────────────────────

all: setup quality security build scan test deploy verify  ## Run full 7-stage CI/CD pipeline

# ── Stage 1: Code Quality ────────────────────────────────────

quality: $(VENV)/.installed lint dupcheck  ## Stage 1 — Lint all services + duplication check
lint:  ## Run linters for all services
	$(MAKE) -C alert-ingestion-service lint PYTHON=$(CURDIR)/$(PYTHON)
	$(MAKE) -C incident-management-service lint PYTHON=$(CURDIR)/$(PYTHON)
	$(MAKE) -C notification-service lint PYTHON=$(CURDIR)/$(PYTHON)
	$(MAKE) -C oncall-service lint PYTHON=$(CURDIR)/$(PYTHON)
	$(MAKE) -C ai-analysis-service lint PYTHON=$(CURDIR)/$(PYTHON)

dupcheck:  ## Check for code duplication (< 3% threshold)
	@echo "── duplication check ──"
	@if command -v jscpd >/dev/null 2>&1; then \
		jscpd alert-ingestion-service/app/ incident-management-service/app/ oncall-service/app/ notification-service/app/ ai-analysis-service/app/ \
			--min-lines 5 --min-tokens 50 --threshold 3 \
			--reporters console \
			--ignore 'node_modules|.venv|htmlcov|__pycache__' || exit 1; \
	else \
		$(PYTHON) -m pylint --disable=all --enable=R0801 \
			alert-ingestion-service/app/ incident-management-service/app/ \
			oncall-service/app/ notification-service/app/ ai-analysis-service/app/ \
			--min-similarity-lines=5 2>&1 | tee /tmp/dupcheck.txt; \
		if grep -q 'R0801' /tmp/dupcheck.txt; then \
			echo "WARN Duplicate code detected (see above)"; \
		else \
			echo "OK No significant duplication found"; \
		fi; \
	fi

# ── Stage 2: Security Scanning ───────────────────────────────

security:  ## Stage 2 — Scan for leaked secrets (gitleaks + trufflehog)
	@echo "── gitleaks ──"
	@if command -v gitleaks >/dev/null 2>&1; then \
		gitleaks detect --source=. --config=.gitleaks.toml -v 2>&1; \
	else \
		echo "SKIP gitleaks not installed"; \
	fi
	@echo "── trufflehog ──"
	@if command -v trufflehog >/dev/null 2>&1; then \
		trufflehog filesystem . --no-update --fail 2>&1; \
	else \
		echo "SKIP trufflehog not installed"; \
	fi

# ── Stage 3: Build Docker Images ─────────────────────────────

build: .env  ## Stage 3 — Build all Docker images
	$(COMPOSE) build --build-arg VERSION=$(VERSION)

# ── Stage 4: Vulnerability Scan ──────────────────────────────

scan: build  ## Stage 4 — Trivy vulnerability scan on all images
	@for img in $(IMAGE_ALERT) $(IMAGE_INCIDENT) $(IMAGE_NOTIF) $(IMAGE_ONCALL) $(IMAGE_AI); do \
		echo "── trivy scan: $$img ──"; \
		trivy image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 0 $$img:latest 2>/dev/null || \
			docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
				aquasec/trivy:latest image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 0 $$img:latest; \
	done

# ── Stage 5: Tests ────────────────────────────────────────────

test: $(VENV)/.installed  ## Stage 5 — Run unit tests with coverage
	$(MAKE) -C alert-ingestion-service test PYTHON=$(CURDIR)/$(PYTHON)
	$(MAKE) -C incident-management-service test PYTHON=$(CURDIR)/$(PYTHON)
	$(MAKE) -C notification-service test PYTHON=$(CURDIR)/$(PYTHON)
	$(MAKE) -C oncall-service test PYTHON=$(CURDIR)/$(PYTHON)
	$(MAKE) -C ai-analysis-service test PYTHON=$(CURDIR)/$(PYTHON)

test-integration: $(VENV)/.installed  ## Run integration tests (requires running services)
	$(MAKE) -C alert-ingestion-service test-integration PYTHON=$(CURDIR)/$(PYTHON)
	$(MAKE) -C incident-management-service test-integration PYTHON=$(CURDIR)/$(PYTHON)
	$(MAKE) -C notification-service test-integration PYTHON=$(CURDIR)/$(PYTHON) 2>/dev/null || true
	$(MAKE) -C oncall-service test-integration PYTHON=$(CURDIR)/$(PYTHON) 2>/dev/null || true
	$(MAKE) -C ai-analysis-service test-integration PYTHON=$(CURDIR)/$(PYTHON) 2>/dev/null || true

# ── Stage 6: Deploy ──────────────────────────────────────────

deploy: .env  ## Stage 6 — Tag prev images for rollback, then deploy
	@echo "── tagging current images as :prev for rollback ──"
	@docker tag $(IMAGE_ALERT):latest $(IMAGE_ALERT):$(PREV_TAG) 2>/dev/null || true
	@docker tag $(IMAGE_INCIDENT):latest $(IMAGE_INCIDENT):$(PREV_TAG) 2>/dev/null || true
	@docker tag $(IMAGE_NOTIF):latest $(IMAGE_NOTIF):$(PREV_TAG) 2>/dev/null || true
	@docker tag $(IMAGE_ONCALL):latest $(IMAGE_ONCALL):$(PREV_TAG) 2>/dev/null || true
	@docker tag $(IMAGE_AI):latest $(IMAGE_AI):$(PREV_TAG) 2>/dev/null || true
	@echo "── deploying ──"
	$(COMPOSE) down -v --remove-orphans 2>/dev/null || true
	$(COMPOSE) up -d --build
	@echo "Waiting for database to be healthy…"
	@until docker inspect --format='{{.State.Health.Status}}' $(DB_CONTAINER) 2>/dev/null | grep -q healthy; do \
		sleep 2; \
	done
	@echo "OK Database is healthy"
	@echo "Waiting for alert-ingestion to be healthy..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		curl -sf http://localhost:8001/health >/dev/null 2>&1 && break; \
		sleep 2; \
	done
	@curl -sf http://localhost:8001/health >/dev/null 2>&1 && echo "OK Alert Ingestion is healthy" || echo "WARN Alert Ingestion not responding yet"
	@echo "Waiting for incident-management to be healthy…"
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		curl -sf http://localhost:8002/health >/dev/null 2>&1 && break; \
		sleep 2; \
	done
	@curl -sf http://localhost:8002/health >/dev/null 2>&1 && echo "OK Incident Management is healthy" || echo "WARN Incident Management not responding yet"
	@echo "Waiting for notification-service to be healthy…"
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		curl -sf http://localhost:8004/health >/dev/null 2>&1 && break; \
		sleep 2; \
	done
	@curl -sf http://localhost:8004/health >/dev/null 2>&1 && echo "OK Notification Service is healthy" || echo "WARN Notification Service not responding yet"
	@echo "Waiting for oncall-service to be healthy..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		curl -sf http://localhost:8003/health >/dev/null 2>&1 && break; \
		sleep 2; \
	done
	@curl -sf http://localhost:8003/health >/dev/null 2>&1 && echo "OK On-Call Service is healthy" || echo "WARN On-Call Service not responding yet"
	@echo "Waiting for ai-analysis to be healthy..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		curl -sf http://localhost:8005/health >/dev/null 2>&1 && break; \
		sleep 2; \
	done
	@curl -sf http://localhost:8005/health >/dev/null 2>&1 && echo "OK AI Analysis is healthy" || echo "WARN AI Analysis not responding yet"
	@echo "Services:"
	@echo "  Alert Ingestion       → http://localhost:8001"
	@echo "  Incident Management   → http://localhost:8002"
	@echo "  On-Call Service       → http://localhost:8003"
	@echo "  Notification Service  → http://localhost:8004"
	@echo "  AI Analysis           → http://localhost:8005"
	@echo "  Database              → localhost:5432"

# ── Stage 7: Verify & Smoke Test ─────────────────────────────

verify:  ## Stage 7 — Health checks + smoke tests (auto-rollback on failure)
	@echo "── health check ──"
	@VERIFY_PASS=true; \
	echo "── alert-ingestion health ──"; \
	curl -sf http://localhost:8001/health | python3 -m json.tool || VERIFY_PASS=false; \
	curl -sf http://localhost:8001/health/ready | python3 -m json.tool || VERIFY_PASS=false; \
	curl -sf http://localhost:8001/health/live  | python3 -m json.tool || VERIFY_PASS=false; \
	echo "── incident-management health ──"; \
	curl -sf http://localhost:8002/health | python3 -m json.tool || VERIFY_PASS=false; \
	curl -sf http://localhost:8002/health/ready | python3 -m json.tool || VERIFY_PASS=false; \
	curl -sf http://localhost:8002/health/live  | python3 -m json.tool || VERIFY_PASS=false; \
	echo "── notification-service health ──"; \
	curl -sf http://localhost:8004/health | python3 -m json.tool || VERIFY_PASS=false; \
	curl -sf http://localhost:8004/health/ready | python3 -m json.tool || VERIFY_PASS=false; \
	curl -sf http://localhost:8004/health/live  | python3 -m json.tool || VERIFY_PASS=false; \
	echo "── smoke test: POST alert ──"; \
	curl -sf -X POST http://localhost:8001/api/v1/alerts \
		-H "Content-Type: application/json" \
		-d '{"service":"make-smoke","severity":"low","message":"root Makefile smoke test"}' | python3 -m json.tool || VERIFY_PASS=false; \
	echo "── smoke test: POST incident ──"; \
	curl -sf -X POST http://localhost:8002/api/v1/incidents \
		-H "Content-Type: application/json" \
		-d '{"title":"[LOW] smoke: verify","service":"make-smoke","severity":"low"}' | python3 -m json.tool || VERIFY_PASS=false; \
	echo "── smoke test: GET incidents ──"; \
	curl -sf "http://localhost:8002/api/v1/incidents?service=make-smoke" | python3 -m json.tool || VERIFY_PASS=false; \
	echo "── verify metrics ──"; \
	curl -sf http://localhost:8001/metrics | grep -q "alerts_received_total" && echo "alert metrics OK" || VERIFY_PASS=false; \
	curl -sf http://localhost:8002/metrics | grep -q "incidents_total" && echo "incident metrics OK" || VERIFY_PASS=false; \
	curl -sf http://localhost:8004/metrics | grep -q "oncall_notifications_sent_total" && echo "notification metrics OK" || VERIFY_PASS=false; \
	echo "── oncall-service health ──"; \
	curl -sf http://localhost:8003/health | python3 -m json.tool || VERIFY_PASS=false; \
	curl -sf http://localhost:8003/health/ready | python3 -m json.tool || VERIFY_PASS=false; \
	curl -sf http://localhost:8003/health/live  | python3 -m json.tool || VERIFY_PASS=false; \
	curl -sf http://localhost:8003/metrics | grep -q "escalations_total" && echo "oncall metrics OK" || VERIFY_PASS=false; \
	echo "── ai-analysis health ──"; \
	curl -sf http://localhost:8005/health | python3 -m json.tool || VERIFY_PASS=false; \
	curl -sf http://localhost:8005/metrics | grep -q "http_request" && echo "ai-analysis metrics OK" || VERIFY_PASS=false; \
	if [ "$$VERIFY_PASS" = "false" ]; then \
		echo "FAIL Verification FAILED -- rolling back to :prev"; \
		$(MAKE) rollback; \
		exit 1; \
	fi; \
	echo "OK All verifications passed"

# ── Rollback ─────────────────────────────────────────────────

rollback:  ## Rollback to :prev tagged images
	@echo "── rolling back ──"
	@docker tag $(IMAGE_ALERT):$(PREV_TAG) $(IMAGE_ALERT):latest 2>/dev/null || echo "No :prev alert image found"
	@docker tag $(IMAGE_INCIDENT):$(PREV_TAG) $(IMAGE_INCIDENT):latest 2>/dev/null || echo "No :prev incident image found"
	@docker tag $(IMAGE_NOTIF):$(PREV_TAG) $(IMAGE_NOTIF):latest 2>/dev/null || echo "No :prev notification image found"
	@docker tag $(IMAGE_ONCALL):$(PREV_TAG) $(IMAGE_ONCALL):latest 2>/dev/null || echo "No :prev oncall image found"
	@docker tag $(IMAGE_AI):$(PREV_TAG) $(IMAGE_AI):latest 2>/dev/null || echo "No :prev ai-analysis image found"
	$(COMPOSE) down -v --remove-orphans 2>/dev/null || true
	$(COMPOSE) up -d
	@echo "Rollback complete — waiting for health…"
	@sleep 10
	@curl -sf http://localhost:8001/health | python3 -m json.tool || echo "WARN Service not healthy after rollback"

# ── Docker Compose Helpers ────────────────────────────────────

up: .env  ## Start all services (detached)
	$(COMPOSE) up -d
	@echo "Waiting for database to be healthy…"
	@until docker inspect --format='{{.State.Health.Status}}' $(DB_CONTAINER) 2>/dev/null | grep -q healthy; do \
		sleep 2; \
	done
	@echo "OK Database is healthy"

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

# ── Convenience ──────────────────────────────────────────────

ci: setup quality security test  ## Run non-Docker CI stages (1, 2, 5)

coverage: $(VENV)/.installed  ## Run tests with coverage and open HTML report
	$(MAKE) -C alert-ingestion-service test PYTHON=$(CURDIR)/$(PYTHON)
	$(MAKE) -C incident-management-service test PYTHON=$(CURDIR)/$(PYTHON)
	$(MAKE) -C notification-service test PYTHON=$(CURDIR)/$(PYTHON)
	$(MAKE) -C oncall-service test PYTHON=$(CURDIR)/$(PYTHON)
	$(MAKE) -C ai-analysis-service test PYTHON=$(CURDIR)/$(PYTHON)
	@echo "Opening coverage report…"
	@xdg-open alert-ingestion-service/htmlcov/index.html 2>/dev/null || open alert-ingestion-service/htmlcov/index.html 2>/dev/null || echo "Report at alert-ingestion-service/htmlcov/index.html"
	@xdg-open incident-management-service/htmlcov/index.html 2>/dev/null || open incident-management-service/htmlcov/index.html 2>/dev/null || echo "Report at incident-management-service/htmlcov/index.html"
	@xdg-open notification-service/htmlcov/index.html 2>/dev/null || open notification-service/htmlcov/index.html 2>/dev/null || echo "Report at notification-service/htmlcov/index.html"

health:  ## Hit health endpoints
	@echo "── Alert Ingestion ──"
	@curl -sf http://localhost:8001/health | python3 -m json.tool
	@curl -sf http://localhost:8001/health/ready | python3 -m json.tool
	@curl -sf http://localhost:8001/health/live  | python3 -m json.tool
	@echo "── Incident Management ──"
	@curl -sf http://localhost:8002/health | python3 -m json.tool
	@curl -sf http://localhost:8002/health/ready | python3 -m json.tool
	@curl -sf http://localhost:8002/health/live  | python3 -m json.tool
	@echo "── Notification Service ──"
	@curl -sf http://localhost:8004/health | python3 -m json.tool
	@curl -sf http://localhost:8004/health/ready | python3 -m json.tool
	@curl -sf http://localhost:8004/health/live  | python3 -m json.tool
	@echo "── On-Call Service ──"
	@curl -sf http://localhost:8003/health | python3 -m json.tool
	@curl -sf http://localhost:8003/health/ready | python3 -m json.tool
	@curl -sf http://localhost:8003/health/live  | python3 -m json.tool
	@echo "── AI Analysis ──"
	@curl -sf http://localhost:8005/health | python3 -m json.tool

smoke:  ## Quick smoke test (POST + GET alert)
	@echo "── POST alert ──"
	@curl -sf -X POST http://localhost:8001/api/v1/alerts \
		-H "Content-Type: application/json" \
		-d '{"service":"make-smoke","severity":"low","message":"root Makefile smoke test"}' | python3 -m json.tool
	@echo "── GET alerts ──"
	@curl -sf "http://localhost:8001/api/v1/alerts?service=make-smoke" | python3 -m json.tool

# ── Formatting ───────────────────────────────────────────────

fmt: $(VENV)/.installed  ## Auto-format all service code
	$(MAKE) -C alert-ingestion-service fmt PYTHON=$(CURDIR)/$(PYTHON)
	$(MAKE) -C incident-management-service fmt PYTHON=$(CURDIR)/$(PYTHON)
	$(MAKE) -C notification-service fmt PYTHON=$(CURDIR)/$(PYTHON)
	$(MAKE) -C oncall-service fmt PYTHON=$(CURDIR)/$(PYTHON)
	$(MAKE) -C ai-analysis-service fmt PYTHON=$(CURDIR)/$(PYTHON)

format: fmt  ## Alias for fmt

# ── Cleanup ──────────────────────────────────────────────────

clean:  ## Remove build artifacts across all services
	$(MAKE) -C alert-ingestion-service clean
	$(MAKE) -C incident-management-service clean
	$(MAKE) -C notification-service clean
	$(MAKE) -C oncall-service clean
	$(MAKE) -C ai-analysis-service clean
	docker image prune -f

fclean: clean  ## Remove everything (venv, volumes, images)
	rm -rf $(VENV)
	$(COMPOSE) down -v --remove-orphans 2>/dev/null || true

# ── Help ─────────────────────────────────────────────────────

help:  ## Show this help
	@grep -E '^[a-zA-Z_%-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'