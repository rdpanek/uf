.PHONY: install test test-api test-e2e test-e2e-headed lint report monitoring-up monitoring-down test-live

install:
	python3 -m venv .venv
	.venv/bin/pip install -U pip
	.venv/bin/pip install -e ".[dev]"
	.venv/bin/playwright install chromium

test:
	.venv/bin/pytest

test-api:
	.venv/bin/pytest -m api

test-e2e:
	.venv/bin/pytest -m e2e

test-e2e-headed:
	.venv/bin/pytest -m e2e --headed --slowmo 300

lint:
	.venv/bin/ruff check . && .venv/bin/ruff format --check .

report:
	open reports/report.html || xdg-open reports/report.html

# Live metrics: Prometheus + Pushgateway + Grafana (needs Docker)
monitoring-up:
	docker compose -f monitoring/docker-compose.yml up -d
	@echo "Grafana: http://localhost:3000  (dashboard 'UniFi OS tests')"

monitoring-down:
	docker compose -f monitoring/docker-compose.yml down

test-live:
	UNIFI_PUSHGATEWAY_URL=http://localhost:9091 .venv/bin/pytest
