.PHONY: build run test lint fmt coverage

SERVICE  := ai-analysis-service
PORT     := 8005

build:
	docker build -t $(SERVICE) .

run:
	docker run --rm -p $(PORT):$(PORT) \
		-e DATABASE_URL=postgresql://incident_user:incident_pass@localhost:5432/incident_platform \
		$(SERVICE)

test:
	python -m pytest tests/ -v --tb=short

lint:
	flake8 app/ tests/

fmt:
	black app/ tests/

coverage:
	python -m pytest tests/ --cov=app --cov-report=html --cov-report=term
