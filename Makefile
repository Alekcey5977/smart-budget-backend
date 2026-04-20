.PHONY: help install clean-venvs start stop restart logs clean load-test-data load-test-images generate-test-data status down build reset-db test test-unit test-e2e test-e2e-start test-e2e-stop k6-smoke k6-load k6-stress k6-spike k6-max k6-high k6-extreme k6

TEST_PROJECT = smartbudget-test
TEST_COMPOSE = docker compose -f docker-compose.test.yml -p $(TEST_PROJECT) --env-file .env.test

PYTHON := $(shell python3 --version > /dev/null 2>&1 && echo python3 || echo python)
# For local venvs: use Python 3.11-3.13 (pydantic-core/asyncpg don't support 3.14 yet)
PYTHON_VENV := $(shell for v in python3.11 python3.12 python3.13 python3; do \
	$$v -c "import sys; exit(0 if sys.version_info < (3,14) else 1)" 2>/dev/null && echo $$v && break; \
done)

help:
	@echo "Smart Budget Backend - Make Commands"
	@echo "====================================="
	@echo ""
	@echo "Main commands:"
	@echo "  make start             - Start all services"
	@echo "  make stop              - Stop all services"
	@echo "  make restart           - Restart all services"
	@echo "  make down              - Stop and remove containers"
	@echo "  make build             - Rebuild all services"
	@echo "  make logs              - Show logs from all services"
	@echo "  make status            - Show service status"
	@echo ""
	@echo "Test data:"
	@echo "  make generate-test-data  - Generate test data files"
	@echo "  make load-test-data      - Load data into pseudo bank"
	@echo "  make load-test-images    - Load images (avatars, icons)"
	@echo ""
	@echo "Setup:"
	@echo "  make install           - Create venvs and install deps for all services"
	@echo ""
	@echo "Testing:"
	@echo "  make test              - Run unit + integration tests for all services"
	@echo "  make test-unit         - Run only unit tests for all services"
	@echo "  make test-e2e-start    - Start isolated test stack (separate DBs, ports 18000+)"
	@echo "  make test-e2e          - Run E2E tests against test stack (port 18000)"
	@echo "  make test-e2e-stop     - Stop and remove test stack (deletes test data)"
	@echo ""
	@echo "Load tests (k6, requires: make test-e2e-start):"
	@echo "  make k6-smoke          - Smoke test: 1 VU, 30s — sanity check"
	@echo "  make k6-load           - Load test: 50 VUs, ~4 min — realistic traffic"
	@echo "  make k6-stress         - Stress test: up to 150 VUs, ~5 min — find limits"
	@echo "  make k6-spike          - Spike test: burst to 1000 VUs, ~1 min"
	@echo "  make k6-max            - Max test: up to 3000 VUs, ~1 min — absolute breaking point"
	@echo "  make k6-high           - High test: up to 5000 VUs, ~75s"
	@echo "  make k6-extreme        - Extreme test: up to 10000 VUs, ~90s — beyond the limit"
	@echo "  make k6                - Run smoke → load → stress in sequence"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean             - Stop services and remove volumes"
	@echo "  make reset-db          - Full DB reset (IDs start from 1)"
	@echo ""

start:
	@echo "Starting all services..."
	docker compose up -d
	@echo ""
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo ""
	@echo "Services started!"
	@echo ""
	@echo "Available services:"
	@echo "  Gateway:               http://localhost:8000"
	@echo "  Gateway Swagger:       http://localhost:8000/docs"
	@echo "  Users Service:         http://localhost:8001/docs"
	@echo "  Transactions:          http://localhost:8002/docs"
	@echo "  Images:                http://localhost:8003/docs"
	@echo "  Pseudo Bank:           http://localhost:8004/docs"
	@echo "  Purposes Service:      http://localhost:8005/docs"
	@echo "  Notifications Service: http://localhost:8006/docs"
	@echo "  History Service:       http://localhost:8007/docs"
	@echo ""
	@echo "Monitoring:"
	@echo "  Grafana:               http://localhost:3000"
	@echo "  Prometheus:            http://localhost:9090"
	@echo "  Redis Commander:       http://localhost:8081"
	@echo ""

stop:
	@echo "Stopping all services..."
	docker compose stop
	@echo "Services stopped!"

restart:
	@echo "Restarting all services..."
	docker compose restart
	@echo "Services restarted!"

down:
	@echo "Stopping and removing containers..."
	docker compose down
	@echo "Containers removed!"

build:
	@echo "Rebuilding all services..."
	docker compose build
	@echo "Services rebuilt!"

logs:
	docker compose logs -f

status:
	@echo "Service Status:"
	@echo "==============="
	docker compose ps

generate-test-data:
	@echo "Generating test data files..."
	cd testData && python3 generate_pseudo_bank_data.py
	cd testData && python3 generate_images_data.py
	@echo ""
	@echo "Test data files generated!"
	@echo "  - testData/pseudo_bank_test_data.json"
	@echo "  - testData/images_data.json"
	@echo "  - testData/test_accounts_info.md"
	@echo ""

load-test-data:
	@echo "Loading test data into pseudo bank..."
	@echo "Make sure services are running (make start)"
	@echo ""
	@sleep 2
	cd testData && python3 load_pseudo_bank_data.py http://localhost:8004
	@echo ""
	@echo "Data loaded! Available account numbers:"
	@echo "  - 40817810099910004312 (Main card)"
	@echo "  - 40817810099910004313 (Savings)"
	@echo "  - 40817810099910004314 (Salary)"
	@echo "  - 40817810099910004315 (Daily)"
	@echo "  - 40817810099910004316 (Credit card)"
	@echo "  - 40817810099910004317 (Currency account)"
	@echo "  - 40817810099910004318 (Family card)"
	@echo "  - 40817810099910004319 (Business account)"
	@echo "  - 40817810099910004320 (Kids card)"
	@echo "  - 40817810099910004321 (Premium card)"
	@echo ""

load-test-images:
	@echo "Loading test images..."
	@echo "Make sure services are running (make start)"
	@echo ""
	docker compose exec -w /app images-service python /testData/load_test_images.py
	@echo ""

clean:
	@echo "Stopping services and removing volumes..."
	@echo "WARNING: All data will be deleted!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose down -v; \
		echo "Cleanup completed!"; \
	else \
		echo "Cleanup cancelled"; \
	fi

clean-venvs:
	@echo "Removing all service virtual environments..."
	@for service in gateway users_service transactions_service purposes_service notification_service history_service images_service pseudo_bank_service; do \
		rm -rf $$service/.venv; \
	done
	@echo "Done! Run 'make install' or 'make test' to recreate them."

install:
	@echo "Creating virtual environments and installing dependencies..."
	@if [ -z "$(PYTHON_VENV)" ]; then echo "ERROR: Python 3.11-3.13 required. Install with: brew install python@3.11"; exit 1; fi
	@for service in gateway users_service transactions_service purposes_service notification_service history_service images_service pseudo_bank_service; do \
		echo "  $$service..."; \
		if [ ! -d "$$service/.venv" ]; then \
			$(PYTHON_VENV) -m venv $$service/.venv; \
		fi; \
		$$service/.venv/bin/pip install -q -r $$service/requirements.txt; \
	done
	@echo "All dependencies installed!"

test:
	@echo "Running unit + integration tests for all services..."
	@echo ""
	@failed=0; \
	for service in gateway users_service transactions_service purposes_service notification_service history_service images_service pseudo_bank_service; do \
		echo "--- $$service ---"; \
		if [ ! -d "$$service/.venv" ]; then \
			echo "  Installing deps for $$service..."; \
			$(PYTHON_VENV) -m venv $$service/.venv && $$service/.venv/bin/pip install -q -r $$service/requirements.txt; \
		fi; \
		cd $$service && .venv/bin/python -m pytest tests/ -q --tb=short 2>&1; \
		if [ $$? -ne 0 ]; then failed=1; fi; \
		cd ..; \
	done; \
	echo ""; \
	if [ $$failed -eq 0 ]; then \
		echo "All tests passed!"; \
	else \
		echo "Some tests failed!"; \
		exit 1; \
	fi

test-unit:
	@echo "Running unit tests for all services..."
	@echo ""
	@failed=0; \
	for service in gateway users_service transactions_service purposes_service notification_service history_service images_service; do \
		echo "--- $$service ---"; \
		if [ ! -d "$$service/.venv" ]; then \
			echo "  Installing deps for $$service..."; \
			$(PYTHON_VENV) -m venv $$service/.venv && $$service/.venv/bin/pip install -q -r $$service/requirements.txt; \
		fi; \
		cd $$service && .venv/bin/python -m pytest tests/unit/ -q --tb=short 2>&1 || true; \
		if [ $$? -ne 0 ]; then failed=1; fi; \
		cd ..; \
	done; \
	echo "--- pseudo_bank_service ---"; \
	if [ ! -d "pseudo_bank_service/.venv" ]; then \
		echo "  Installing deps for pseudo_bank_service..."; \
		$(PYTHON_VENV) -m venv pseudo_bank_service/.venv && pseudo_bank_service/.venv/bin/pip install -q -r pseudo_bank_service/requirements.txt; \
	fi; \
	cd pseudo_bank_service && .venv/bin/python -m pytest tests/ -q --tb=short 2>&1; \
	if [ $$? -ne 0 ]; then failed=1; fi; \
	cd ..; \
	echo ""; \
	if [ $$failed -eq 0 ]; then \
		echo "All unit tests passed!"; \
	else \
		echo "Some unit tests failed!"; \
		exit 1; \
	fi

test-e2e-start:
	@echo "Starting isolated E2E test stack..."
	@echo "  Gateway:      http://localhost:18000"
	@echo "  Pseudo Bank:  http://localhost:18004"
	@echo ""
	$(TEST_COMPOSE) up -d --build
	@echo ""
	@echo "Waiting for gateway to be ready..."
	@for i in $$(seq 1 40); do \
		if curl -sf http://localhost:18000/health > /dev/null 2>&1; then \
			echo "Gateway is ready!"; \
			break; \
		fi; \
		if [ $$i -eq 40 ]; then \
			echo "ERROR: Gateway did not respond after 40 attempts (2 min)"; \
			$(TEST_COMPOSE) logs gateway; \
			exit 1; \
		fi; \
		echo "  waiting... ($$i/40)"; \
		sleep 3; \
	done
	@echo ""
	@echo "Patching containers with prometheus-fastapi-instrumentator..."
	@for svc in gateway users-service transactions-service history-service notification-service purposes-service images-service pseudo-bank-service; do \
		CONTAINER="$(TEST_PROJECT)-$${svc}-1"; \
		echo "  Patching $$CONTAINER..."; \
		docker exec $$CONTAINER pip install prometheus-fastapi-instrumentator==7.1.0 -q 2>/dev/null || true; \
		MAIN_FILE=$$(docker exec $$CONTAINER find /app -name "main.py" -not -path "*/test*" 2>/dev/null | head -1); \
		if [ -n "$$MAIN_FILE" ]; then \
			HAS_INSTR=$$(docker exec $$CONTAINER grep -l "Instrumentator" $$MAIN_FILE 2>/dev/null); \
			if [ -z "$$HAS_INSTR" ]; then \
				docker exec $$CONTAINER sh -c "sed -i '1s/^/from prometheus_fastapi_instrumentator import Instrumentator\n/' $$MAIN_FILE"; \
				docker exec $$CONTAINER sh -c "sed -i 's/if __name__ == \"__main__\":/Instrumentator().instrument(app).expose(app, endpoint=\"\/metrics\")\n\nif __name__ == \"__main__\":/' $$MAIN_FILE" || \
				docker exec $$CONTAINER sh -c "echo 'from prometheus_fastapi_instrumentator import Instrumentator' >> $$MAIN_FILE; echo 'Instrumentator().instrument(app).expose(app, endpoint=\"/metrics\")' >> $$MAIN_FILE"; \
			fi; \
		fi; \
		docker restart $$CONTAINER > /dev/null 2>&1; \
	done
	@echo "Waiting for patched services to restart..."
	@sleep 6
	@echo ""
	@echo "Loading test data into pseudo bank..."
	cd testData && $(PYTHON) load_pseudo_bank_data.py http://localhost:18004
	@echo ""
	@echo "Loading test images..."
	$(TEST_COMPOSE) exec -w /app images-service python3 /testData/load_test_images.py
	@echo ""
	@echo "Test stack ready! Run: make test-e2e"
	@echo "  Gateway:    http://localhost:18000"
	@echo "  Grafana:    http://localhost:13000"
	@echo "  Prometheus: http://localhost:19090"
	@echo ""

test-e2e-stop:
	@echo "Stopping and removing E2E test stack..."
	$(TEST_COMPOSE) down -v
	@echo "Test stack removed (all test data deleted)!"
	@echo ""

test-e2e:
	@echo "Running E2E tests against isolated test stack..."
	@echo "Requires: make test-e2e-start"
	@echo ""
	docker compose -f docker-compose.test.yml -p $(TEST_PROJECT) exec -e GATEWAY_URL=http://localhost:8000 -T gateway python3 -m pytest e2e_tests/ -v --tb=short
	@echo ""

K6_BASE_URL ?= http://localhost:18000
K6_PROMETHEUS_RW ?= http://localhost:9090/api/v1/write
K6_OUT ?= --out experimental-prometheus-rw=$(K6_PROMETHEUS_RW)

k6-smoke:
	@echo "Running smoke test (1 VU, 30s) against $(K6_BASE_URL)..."
	k6 run --env BASE_URL=$(K6_BASE_URL) $(K6_OUT) k6/smoke.js

k6-load:
	@echo "Running load test (50 VUs, ~4 min) against $(K6_BASE_URL)..."
	k6 run --env BASE_URL=$(K6_BASE_URL) $(K6_OUT) k6/load.js

k6-stress:
	@echo "Running stress test (up to 150 VUs, ~5 min) against $(K6_BASE_URL)..."
	k6 run --env BASE_URL=$(K6_BASE_URL) $(K6_OUT) k6/stress.js

k6-spike:
	@echo "Running spike test (burst to 1000 VUs, ~1 min) against $(K6_BASE_URL)..."
	k6 run --env BASE_URL=$(K6_BASE_URL) $(K6_OUT) k6/spike.js

k6-max:
	@echo "Running max test (up to 3000 VUs, ~1 min) against $(K6_BASE_URL)..."
	@echo "WARNING: This test is designed to break the system. For observation only."
	k6 run --env BASE_URL=$(K6_BASE_URL) $(K6_OUT) k6/max.js

k6-high:
	@echo "Running high test (up to 5000 VUs, ~75s) against $(K6_BASE_URL)..."
	k6 run --env BASE_URL=$(K6_BASE_URL) $(K6_OUT) k6/high.js

k6-extreme:
	@echo "Running extreme test (up to 10000 VUs, ~90s) against $(K6_BASE_URL)..."
	@echo "WARNING: Extreme load — system will likely saturate. Observation only."
	k6 run --env BASE_URL=$(K6_BASE_URL) $(K6_OUT) k6/extreme.js

k6:
	@echo "Running smoke → load → stress sequence against $(K6_BASE_URL)..."
	@echo "Requires: make test-e2e-start"
	@echo ""
	@echo "=== [1/3] Smoke ==="
	k6 run --env BASE_URL=$(K6_BASE_URL) $(K6_OUT) k6/smoke.js
	@echo ""
	@echo "=== [2/3] Load ==="
	k6 run --env BASE_URL=$(K6_BASE_URL) $(K6_OUT) k6/load.js
	@echo ""
	@echo "=== [3/3] Stress ==="
	k6 run --env BASE_URL=$(K6_BASE_URL) $(K6_OUT) k6/stress.js
	@echo ""
	@echo "All load tests complete! Check Grafana: http://localhost:3000"

reset-db:
	@echo "=============================================="
	@echo "FULL DATABASE RESET"
	@echo "=============================================="
	@echo "This will delete ALL data and reset IDs to 1"
	@echo ""
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "Stopping services..."; \
		docker compose down -v; \
		echo "Volumes removed, starting services..."; \
		docker compose up -d; \
		echo "Waiting for DB initialization..."; \
		sleep 15; \
		echo ""; \
		echo "Database fully reset!"; \
		echo "All tables are empty, IDs will start from 1"; \
		echo ""; \
		echo "To load test data run:"; \
		echo "  make load-test-data"; \
		echo "  make load-test-images"; \
	else \
		echo "Reset cancelled"; \
	fi
