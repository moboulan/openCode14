# ============================================================
# Incident Platform — Root Makefile
# 7-stage CI/CD pipeline as per hackathon spec
# ============================================================

COMPOSE       := docker compose
SERVICES      := alert-ingestion
DB_CONTAINER  := incident-db
IMAGE_NAME    := expertmind-alert-ingestion
PREV_TAG      := prev
VERSION       := $(shell git rev-parse --short HEAD 2>/dev/null || echo "dev")

.PHONY: all quality security build scan test deploy verify \
        up down down-v restart logs ps \
        db-shell db-reset \
        ci coverage clean help

# ── Full 7-Stage Pipeline ────────────────────────────────────

all: quality security build scan test deploy verify  ## Run full 7-stage CI/CD pipeline

# ── Stage 1: Code Quality ────────────────────────────────────

quality: lint  ## Stage 1 — Lint all services
lint:  ## Run linters for alert-ingestion-service
	$(MAKE) -C alert-ingestion-service lint

# ── Stage 2: Security Scanning ───────────────────────────────

security:  ## Stage 2 — Scan for leaked secrets (gitleaks + trufflehog)
	@echo "── gitleaks ──"
	@gitleaks detect --source=. --config=.gitleaks.toml -v 2>&1 || true
	@echo "── trufflehog ──"
	@trufflehog filesystem . --no-update --fail 2>&1 || true

# ── Stage 3: Build Docker Images ─────────────────────────────

build:  ## Stage 3 — Build all Docker images
	$(COMPOSE) build --build-arg VERSION=$(VERSION)

# ── Stage 4: Vulnerability Scan ──────────────────────────────

scan: build  ## Stage 4 — Trivy vulnerability scan on all images
	@echo "── trivy scan: $(IMAGE_NAME) ──"
	@trivy image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 0 $(IMAGE_NAME):latest 2>/dev/null || \
		docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
			aquasec/trivy:latest image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 0 $(IMAGE_NAME):latest

# ── Stage 5: Tests ────────────────────────────────────────────

test:  ## Stage 5 — Run unit + integration tests with coverage
	$(MAKE) -C alert-ingestion-service test

# ── Stage 6: Deploy ──────────────────────────────────────────

deploy:  ## Stage 6 — Tag prev images for rollback, then deploy
	@echo "── tagging current images as :prev for rollback ──"
	@docker tag $(IMAGE_NAME):latest $(IMAGE_NAME):$(PREV_TAG) 2>/dev/null || true
	@echo "── deploying ──"
	$(COMPOSE) down -v --remove-orphans 2>/dev/null || true
	$(COMPOSE) up -d --build
	@echo "Waiting for database to be healthy…"
	@until docker inspect --format='{{.State.Health.Status}}' $(DB_CONTAINER) 2>/dev/null | grep -q healthy; do \
		sleep 2; \
	done
	@echo "✅ Database is healthy"
	@echo "Waiting for alert-ingestion to be healthy…"
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		curl -sf http://localhost:8001/health >/dev/null 2>&1 && break; \
		sleep 2; \
	done
	@curl -sf http://localhost:8001/health >/dev/null 2>&1 && echo "✅ Alert Ingestion is healthy" || echo "⚠️  Alert Ingestion not responding yet"
	@echo "Services:"
	@echo "  Alert Ingestion  → http://localhost:8001"
	@echo "  Database         → localhost:5432"

# ── Stage 7: Verify & Smoke Test ─────────────────────────────

verify:  ## Stage 7 — Health checks + smoke tests (auto-rollback on failure)
	@echo "── health check ──"
	@VERIFY_PASS=true; \
	curl -sf http://localhost:8001/health | python3 -m json.tool || VERIFY_PASS=false; \
	curl -sf http://localhost:8001/health/ready | python3 -m json.tool || VERIFY_PASS=false; \
	curl -sf http://localhost:8001/health/live  | python3 -m json.tool || VERIFY_PASS=false; \
	echo "── smoke test: POST alert ──"; \
	curl -sf -X POST http://localhost:8001/api/v1/alerts \
		-H "Content-Type: application/json" \
		-d '{"service":"make-smoke","severity":"low","message":"root Makefile smoke test"}' | python3 -m json.tool || VERIFY_PASS=false; \
	echo "── smoke test: GET alerts ──"; \
	curl -sf "http://localhost:8001/api/v1/alerts?service=make-smoke" | python3 -m json.tool || VERIFY_PASS=false; \
	echo "── verify metrics ──"; \
	curl -sf http://localhost:8001/metrics | grep -q "alerts_received_total" && echo "metrics OK" || VERIFY_PASS=false; \
	if [ "$$VERIFY_PASS" = "false" ]; then \
		echo "❌ Verification FAILED — rolling back to :prev"; \
		$(MAKE) rollback; \
		exit 1; \
	fi; \
	echo "✅ All verifications passed"

# ── Rollback ─────────────────────────────────────────────────

rollback:  ## Rollback to :prev tagged images
	@echo "── rolling back ──"
	@docker tag $(IMAGE_NAME):$(PREV_TAG) $(IMAGE_NAME):latest 2>/dev/null || echo "No :prev image found"
	$(COMPOSE) down -v --remove-orphans 2>/dev/null || true
	$(COMPOSE) up -d
	@echo "Rollback complete — waiting for health…"
	@sleep 10
	@curl -sf http://localhost:8001/health | python3 -m json.tool || echo "⚠️  Service not healthy after rollback"

# ── Docker Compose Helpers ────────────────────────────────────

up:  ## Start all services (detached)
	$(COMPOSE) up -d
	@echo "Waiting for database to be healthy…"
	@until docker inspect --format='{{.State.Health.Status}}' $(DB_CONTAINER) 2>/dev/null | grep -q healthy; do \
		sleep 2; \
	done
	@echo "✅ Database is healthy"

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

ci: quality security test  ## Run non-Docker CI stages (1, 2, 5)

coverage:  ## Run tests with coverage and open HTML report
	$(MAKE) -C alert-ingestion-service test
	@echo "Opening coverage report…"
	@xdg-open alert-ingestion-service/htmlcov/index.html 2>/dev/null || open alert-ingestion-service/htmlcov/index.html 2>/dev/null || echo "Report at alert-ingestion-service/htmlcov/index.html"

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