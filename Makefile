.PHONY: up down build logs restart clean help

# Default target
help:
	@echo "Trading Bot Docker Commands"
	@echo "==========================="
	@echo "make build    - Build Docker images"
	@echo "make up       - Start bot and dashboard"
	@echo "make down     - Stop all containers"
	@echo "make logs     - View container logs"
	@echo "make restart  - Restart all containers"
	@echo "make clean    - Remove containers and volumes"

# Build Docker images
build:
	docker-compose build

# Start services
up:
	docker-compose up -d
	@echo "Dashboard running at http://localhost:5000"

# Stop services
down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f

# View bot logs only
logs-bot:
	docker-compose logs -f bot

# View dashboard logs only
logs-dashboard:
	docker-compose logs -f dashboard

# Restart services
restart:
	docker-compose restart

# Clean up containers and volumes
clean:
	docker-compose down -v
	docker system prune -f

# Run bot locally (without Docker)
run-local:
	python bot.py

# Run dashboard locally
run-dashboard:
	python dashboard.py