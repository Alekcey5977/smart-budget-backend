.PHONY: help start stop restart logs clean load-test-data generate-test-data status down build

help:
	@echo "Smart Budget Backend - Make Commands"
	@echo "====================================="
	@echo ""
	@echo "Available commands:"
	@echo "  make start           - Start all services"
	@echo "  make stop            - Stop all services"
	@echo "  make restart         - Restart all services"
	@echo "  make down            - Stop and remove all containers"
	@echo "  make build           - Rebuild all services"
	@echo "  make logs            - Show logs from all services"
	@echo "  make status          - Show status of all services"
	@echo "  make generate-test-data - Generate test data files"
	@echo "  make load-test-data  - Load test data into pseudo bank"
	@echo "  make clean           - Stop services and remove volumes"
	@echo ""

start:
	@echo "Starting all services..."
	docker-compose up -d
	@echo ""
	@echo "Waiting for services to be ready..."
	@sleep 10
	@echo ""
	@echo "Services started successfully!"
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
	@echo "Services stopped successfully!"

restart:
	@echo "Restarting all services..."
	docker-compose restart
	@echo "Services restarted successfully!"

down:
	@echo "Stopping and removing all containers..."
	docker-compose down
	@echo "Containers removed successfully!"

build:
	@echo "Rebuilding all services..."
	docker-compose build
	@echo "Services rebuilt successfully!"

logs:
	docker-compose logs -f

status:
	@echo "Service Status:"
	@echo "==============="
	docker-compose ps

generate-test-data:
	@echo "Generating test data files..."
	cd testData && python generate_pseudo_bank_data.py
	@echo ""
	@echo "Test data files generated successfully!"
	@echo "  - testData/pseudo_bank_test_data.json"
	@echo "  - testData/test_accounts_info.md"
	@echo ""

load-test-data:
	@echo "Loading test data into pseudo bank..."
	@echo "Make sure services are running (make start)"
	@echo ""
	@sleep 2
	cd testData && python load_pseudo_bank_data.py http://localhost:8004
	@echo ""
	@echo "Test data loaded! You can now use these account numbers:"
	@echo "  - 40817810099910004312"
	@echo "  - 40817810099910004313"
	@echo "  - 40817810099910004314"
	@echo "  - 40817810099910004315"
	@echo ""

clean:
	@echo "Stopping services and removing volumes..."
	@echo "WARNING: This will delete all database data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		echo "Cleanup completed!"; \
	else \
		echo "Cleanup cancelled"; \
	fi
