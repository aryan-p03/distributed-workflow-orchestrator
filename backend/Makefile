.PHONY: dev
dev: ## Starts the development server
	uv run uvicorn backend.app:create_app --factory --reload

.PHONY: build
build: ## Builds the application
	uv build

.PHONY: test
test: ## Runs tests using pytest
	uv run pytest

.PHONY: lint
lint: ## Runs Ruff for linting
	uv run ruff check .

.PHONY: format
format: ## Formats the codebase using Ruff
	uv run ruff format .

.PHONY: format-check
format-check: ## Checks if the codebase is formatted using Ruff
	uv run ruff format --check .

.PHONY: typecheck
typecheck: ## Runs Mypy for type checking
	uv run mypy src tests main.py

.PHONY: audit
audit: ## Runs checks for security vulnerabilities on dependencies using pip-audit
	uv run pip-audit

.PHONY: check
check: lint typecheck format-check ## Runs all checks (linting, type checking, formatting)