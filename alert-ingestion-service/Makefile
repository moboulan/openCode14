# ============================================================
# Alert Ingestion Service — Local CI/CD Makefile
# Mirrors the 7-stage GitHub Actions pipeline for local use.
# ============================================================

SERVICE_DIR   := .
PYTHON        := python
PIP           := pip
APP_MODULE    := app
TESTS_DIR     := tests
IMAGE_NAME    := expertmind-alert-ingestion
COVERAGE_MIN  := 100

.PHONY: all lint security build scan test deploy verify clean help

all: lint security test  ## Run non-Docker stages (1, 2, 5)

# ── Stage 1: Code Quality ───────────────────────────────────

lint: lint-flake8 lint-pylint lint-black lint-isort  ## Run all linters

lint-flake8:
	@echo "── flake8 ──"
	cd $(SERVICE_DIR) && $(PYTHON) -m flake8 $(APP_MODULE)/ \
		--max-line-length=120 \
		--ignore=E501,W503,E402 \
		--statistics

lint-pylint:
	@echo "── pylint ──"
	cd $(SERVICE_DIR) && $(PYTHON) -m pylint $(APP_MODULE)/ \
		--disable=C0114,C0115,C0116,C0301,R0903,R0914,E0401,W0603,W0621,W0613,W1203 \
		--fail-under=7.0

lint-black:
	@echo "── black --check ──"
	cd $(SERVICE_DIR) && $(PYTHON) -m black --check --line-length=120 $(APP_MODULE)/

lint-isort:
	@echo "── isort --check ──"
	cd $(SERVICE_DIR) && $(PYTHON) -m isort --check --profile=black $(APP_MODULE)/

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
	@curl -sf http://localhost:8001/health | python3 -m json.tool
	@curl -sf http://localhost:8001/health/ready | python3 -m json.tool
	@curl -sf http://localhost:8001/health/live  | python3 -m json.tool
	@echo "── smoke test: POST alert ──"
	@curl -sf -X POST http://localhost:8001/api/v1/alerts \
		-H "Content-Type: application/json" \
		-d '{"service":"make-smoke","severity":"low","message":"Makefile smoke test"}' | python3 -m json.tool
	@echo "── smoke test: GET alerts ──"
	@curl -sf "http://localhost:8001/api/v1/alerts?service=make-smoke" | python3 -m json.tool
	@echo "── verify metrics ──"
	@curl -sf http://localhost:8001/metrics | grep -c "alerts_received_total" > /dev/null && echo "metrics OK"

# ── Utilities ────────────────────────────────────────────────

install-dev:  ## Install dev / test dependencies
	$(PYTHON) -m pip install -r $(SERVICE_DIR)/requirements.txt
	$(PYTHON) -m pip install flake8 pylint black isort pytest pytest-cov pytest-asyncio httpx

fmt:  ## Auto-format code
	cd $(SERVICE_DIR) && $(PYTHON) -m black --line-length=120 $(APP_MODULE)/ $(TESTS_DIR)/
	cd $(SERVICE_DIR) && $(PYTHON) -m isort --profile=black $(APP_MODULE)/ $(TESTS_DIR)/

format: fmt  ## Alias for fmt

clean:  ## Remove build artifacts

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
