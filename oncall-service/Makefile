# ============================================================
# On-Call Service — Local CI/CD Makefile
# Mirrors the 7-stage GitHub Actions pipeline for local use.
# ============================================================

SERVICE_DIR   := .
PYTHON        := python
PIP           := pip
APP_MODULE    := app
TESTS_DIR     := tests
IMAGE_NAME    := expertmind-oncall-service
COVERAGE_MIN  := 100

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
	trivy image --severity HIGH,CRITICAL --exit-code 0 $(IMAGE_NAME):latest

# ── Stage 5: Testing ─────────────────────────────────────────

test:  ## Run unit tests with coverage
	@echo "── pytest ──"
	cd $(SERVICE_DIR) && $(PYTHON) -m pytest $(TESTS_DIR)/ \
		--ignore=$(TESTS_DIR)/integration \
		-v --tb=short \
		--cov=$(APP_MODULE) \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=$(COVERAGE_MIN)

# ── Stage 6: Deploy (Docker Compose) ────────────────────────

deploy:  ## Deploy via docker compose
	@echo "── deploying ──"
	cd .. && docker compose up -d --build oncall-service

# ── Stage 7: Verify ─────────────────────────────────────────

verify:  ## Health check
	@echo "── verifying service health ──"
	@for i in $$(seq 1 30); do \
		curl -sf http://localhost:8003/health > /dev/null 2>&1 && \
		echo "OK oncall-service healthy" && exit 0; \
		sleep 1; \
	done; \
	echo "FAIL oncall-service unhealthy after 30s" && exit 1

# ── Helpers ──────────────────────────────────────────────────

clean:  ## Remove build artifacts
	rm -rf __pycache__ .pytest_cache htmlcov .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

format: ## Auto-format code
	cd $(SERVICE_DIR) && $(PYTHON) -m ruff format $(APP_MODULE)/ $(TESTS_DIR)/
	cd $(SERVICE_DIR) && $(PYTHON) -m ruff check --fix $(APP_MODULE)/ $(TESTS_DIR)/

fmt: format  ## Alias for format

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
