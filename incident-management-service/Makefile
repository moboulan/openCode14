# ============================================================
# Incident Management Service — Local CI/CD Makefile
# Mirrors the 7-stage GitHub Actions pipeline for local use.
# ============================================================

SERVICE_DIR   := .
PYTHON        := python
PIP           := pip
APP_MODULE    := app
TESTS_DIR     := tests
IMAGE_NAME    := expertmind-incident-management
COVERAGE_MIN  := 60

.PHONY: all lint security build scan test deploy verify clean help

all: lint security test  ## Run non-Docker stages (1, 2, 5)

# ── Stage 1: Code Quality ───────────────────────────────────

lint:  ## Lint with ruff
	@echo "── ruff check ──"
	cd $(SERVICE_DIR) && $(PYTHON) -m ruff check $(APP_MODULE)/
	@echo "── ruff format --check ──"
	cd $(SERVICE_DIR) && $(PYTHON) -m ruff format --check $(APP_MODULE)/

# ── Stage 2: Security Scanning ──────────────────────────────

security:  ## Scan for leaked secrets
	@echo "── gitleaks ──"
	gitleaks detect --source=.. --config=../.gitleaks.toml -v || true
	@echo "── trufflehog ──"
	trufflehog filesystem .. --no-update --fail || true

# ── Stage 3: Build Docker Image ─────────────────────────────

build:  ## Build Docker image
	@echo "── docker build ──"
	docker build -t $(IMAGE_NAME):latest $(SERVICE_DIR)
	@docker images $(IMAGE_NAME) --format "{{.Repository}}:{{.Tag}} — {{.Size}}"

# ── Stage 4: Vulnerability Scan ──────────────────────────────

scan: build  ## Scan image with Trivy
	@echo "── trivy ──"
	trivy image --severity HIGH,CRITICAL --ignore-unfixed $(IMAGE_NAME):latest

# ── Stage 5: Tests ───────────────────────────────────────────

test:  ## Run unit tests with coverage (excludes integration)
	@echo "── pytest ──"
	cd $(SERVICE_DIR) && $(PYTHON) -m pytest $(TESTS_DIR)/ -v \
		--ignore=$(TESTS_DIR)/integration \
		--tb=short \
		--cov=$(APP_MODULE) \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=$(COVERAGE_MIN)

test-integration:  ## Run integration tests (requires running DB)
	@echo "── integration tests ──"
	cd $(SERVICE_DIR) && $(PYTHON) -m pytest $(TESTS_DIR)/integration/ -v --tb=short

test-all:  ## Run all tests (unit + integration)
	cd $(SERVICE_DIR) && $(PYTHON) -m pytest $(TESTS_DIR)/ -v \
		--tb=short \
		--cov=$(APP_MODULE) \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=$(COVERAGE_MIN)

test-quick:  ## Run tests without coverage
	cd $(SERVICE_DIR) && $(PYTHON) -m pytest $(TESTS_DIR)/ -v --tb=short

# ── Stage 6: Deploy (Docker Compose) ────────────────────────

deploy: build  ## Deploy via Docker Compose
	@echo "── deploy ──"
	cd .. && docker compose down -v --remove-orphans 2>/dev/null || true
	cd .. && docker compose up -d --build
	@echo "Waiting 30s for services to start…"
	@sleep 30

# ── Stage 7: Verify & Smoke Test ────────────────────────────

verify:  ## Run health & smoke tests against running service
	@echo "── health check ──"
	@curl -sf http://localhost:8002/health | python3 -m json.tool
	@curl -sf http://localhost:8002/health/ready | python3 -m json.tool
	@curl -sf http://localhost:8002/health/live  | python3 -m json.tool
	@echo "── smoke test: POST incident ──"
	@curl -sf -X POST http://localhost:8002/api/v1/incidents \
		-H "Content-Type: application/json" \
		-d '{"title":"[LOW] test-svc: Makefile smoke test","service":"test-svc","severity":"low","description":"Smoke test"}' | python3 -m json.tool
	@echo "── smoke test: GET incidents ──"
	@curl -sf "http://localhost:8002/api/v1/incidents?service=test-svc" | python3 -m json.tool
	@echo "── verify metrics ──"
	@curl -sf http://localhost:8002/metrics | grep -c "incidents_total" > /dev/null && echo "metrics OK"

# ── Utilities ────────────────────────────────────────────────

install-dev:  ## Install dev / test dependencies
	$(PYTHON) -m pip install -r $(SERVICE_DIR)/requirements.txt
	$(PYTHON) -m pip install ruff pytest pytest-cov pytest-asyncio httpx

fmt:  ## Auto-format code
	cd $(SERVICE_DIR) && $(PYTHON) -m ruff format $(APP_MODULE)/ $(TESTS_DIR)/
	cd $(SERVICE_DIR) && $(PYTHON) -m ruff check --fix $(APP_MODULE)/ $(TESTS_DIR)/

format: fmt  ## Alias for fmt

clean:  ## Remove build artifacts
	rm -rf htmlcov .coverage .pytest_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
