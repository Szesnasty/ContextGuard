# ContextGuard — canonical monorepo verbs.
# Every phase's Definition of Done calls these. Stubs echo + exit 0 where the
# real target does not exist yet, so the contract is stable from day one.

.DEFAULT_GOAL := help
.PHONY: help up down seed test e2e lint types fmt demo layout

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

up: ## Start the local stack (compose)
	@command -v docker >/dev/null 2>&1 \
		&& docker compose up -d \
		|| echo "up: compose stack not defined yet (phase 0.3)"

down: ## Stop the local stack
	@command -v docker >/dev/null 2>&1 \
		&& docker compose down \
		|| echo "down: compose stack not defined yet (phase 0.3)"

seed: ## Load tenant + policy fixtures
	@echo "seed: not implemented in phase 0"

test: ## Run Python + JS unit tests
	uv run pytest
	pnpm -r --if-present test

e2e: ## Run end-to-end tests (Playwright)
	@echo "e2e: not implemented in phase 0"

lint: ## Lint Python + JS
	uv run ruff check .
	pnpm -r --if-present lint

types: ## Type-check Python (mypy) + JS (vue-tsc)
	uv run mypy
	@echo "types(js): not implemented in phase 0"

fmt: ## Format Python + JS
	uv run ruff format .
	@command -v pnpm >/dev/null 2>&1 && pnpm -r --if-present format || true

demo: ## Run the demo flow
	@echo "demo: not implemented in phase 0"

layout: ## Assert the monorepo layout matches ADR-003
	python3 scripts/check_layout.py
