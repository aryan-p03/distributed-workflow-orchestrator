.PHONY: dev
dev: ## Starts the development server
	npm run dev

.PHONY: build
build: ## Builds the frontend application
	npm run build

.PHONY: test
test: ## Runs Vitest in watch mode
	npm test

.PHONY: test-run
test-run: ## Runs tests once using Vitest
	npm run test:run

.PHONY: test-coverage
test-coverage: ## Runs tests with coverage
	npm run test:coverage

.PHONY: lint
lint: ## Runs ESlint on the codebase
	npm run lint

.PHONY: typecheck
typecheck: ## Runs TypeScript type checking
	npm run typecheck

.PHONY: format
format: ## Formats the codebase using Prettier
	npm run format

.PHONY: format-check
format-check: ## Checks if the codebase is formatted using Prettier
	npm run format:check

.PHONY: audit
audit: ## Runs checks for security vulnerabilities on dependencies (including transient ones)
	npm run audit

.PHONY: check
check: lint typecheck format-check ## Runs all checks (linting, type checking, formatting)