
.PHONY: help up up-build down logs logs-api logs-frontend logs-worker ps restart restart-api restart-frontend restart-worker rebuild-api rebuild-frontend clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "%-20s %s\n", $$1, $$2}'

up: ## Boot stack quickly (no image rebuild)
	docker compose up -d

up-build: ## Boot stack and rebuild images
	docker compose up --build -d

down: ## Stop and remove containers
	docker compose down

logs: ## Tail all service logs
	docker compose logs -f --tail=150

logs-api: ## Tail API logs
	docker compose logs -f --tail=150 api

logs-frontend: ## Tail frontend logs
	docker compose logs -f --tail=150 frontend

logs-worker: ## Tail worker logs
	docker compose logs -f --tail=150 worker

ps: ## Show service status
	docker compose ps

restart: ## Restart core runtime services
	docker compose restart api worker frontend

restart-api: ## Restart API service only
	docker compose restart api

restart-frontend: ## Restart frontend service only
	docker compose restart frontend

restart-worker: ## Restart worker service only
	docker compose restart worker

rebuild-api: ## Rebuild and restart API service
	docker compose up -d --build api

rebuild-frontend: ## Rebuild and restart frontend service
	docker compose up -d --build frontend

clean: ## Tear down everything including volumes
	docker compose down --volumes --remove-orphans
