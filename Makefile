.PHONY: help build run stop logs clean test api-docs

help:
	@echo "Available commands:"
	@echo "  make build      - Build the Docker image"
	@echo "  make run        - Run the API server in Docker"
	@echo "  make stop       - Stop the API server"
	@echo "  make logs       - View API server logs"
	@echo "  make clean      - Remove containers and images"
	@echo "  make test       - Run API tests"
	@echo "  make api-docs   - Open API documentation in browser"
	@echo "  make dev        - Run API server locally (without Docker)"

build:
	docker-compose build

run:
	docker-compose up -d
	@echo "API server is running at http://localhost:8000"
	@echo "API docs available at http://localhost:8000/docs"

stop:
	docker-compose down

logs:
	docker-compose logs -f

clean:
	docker-compose down -v --rmi all

test:
	@echo "Running API tests..."
	pytest tests/test_api_server.py -v

api-docs:
	@echo "Opening API documentation..."
	@open http://localhost:8000/docs || xdg-open http://localhost:8000/docs || start http://localhost:8000/docs

dev:
	@echo "Starting API server in development mode..."
	python -m claude_agent_sdk.api_server --reload
