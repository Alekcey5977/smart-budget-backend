.PHONY: help start stop restart logs clean load-test-data load-test-images generate-test-data status down build reset-db

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
	@echo "Cleanup:"
	@echo "  make clean             - Stop services and remove volumes"
	@echo "  make reset-db          - Full DB reset (IDs start from 1)"
	@echo ""

start:
	@echo "Starting all services..."
	docker-compose up -d
	@echo ""
	@echo "Waiting for services to be ready..."
	@sleep 10
	@echo ""
	@echo "Services started!"
	@echo ""
	@echo "Available services:"
	@echo "  Gateway:             http://localhost:8000"
	@echo "  Gateway Swagger:     http://localhost:8000/docs"
	@echo "  Users Service:       http://localhost:8001/docs"
	@echo "  Transactions:        http://localhost:8002/docs"
	@echo "  Images:              http://localhost:8003/docs"
	@echo "  Pseudo Bank:         http://localhost:8004/docs"
	@echo ""

stop:
	@echo "Stopping all services..."
	docker-compose stop
	@echo "Services stopped!"

restart:
	@echo "Restarting all services..."
	docker-compose restart
	@echo "Services restarted!"

down:
	@echo "Stopping and removing containers..."
	docker-compose down
	@echo "Containers removed!"

build:
	@echo "Rebuilding all services..."
	docker-compose build
	@echo "Services rebuilt!"

logs:
	docker-compose logs -f

status:
	@echo "Service Status:"
	@echo "==============="
	docker-compose ps

generate-test-data:
	@echo "Generating test data files..."
	cd testData && python generate_pseudo_bank_data.py
	cd testData && python generate_images_data.py
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
	cd testData && python load_pseudo_bank_data.py http://localhost:8004
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
	docker-compose exec -w /app images-service python /testData/load_test_images.py
	@echo ""

clean:
	@echo "Stopping services and removing volumes..."
	@echo "WARNING: All data will be deleted!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		echo "Cleanup completed!"; \
	else \
		echo "Cleanup cancelled"; \
	fi

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
		docker-compose down -v; \
		echo "Volumes removed, starting services..."; \
		docker-compose up -d; \
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
