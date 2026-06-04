# ContextGuard — canonical monorepo verbs.
# Every phase's Definition of Done calls these. Stubs echo + exit 0 where the
# real target does not exist yet, so the contract is stable from day one.

.DEFAULT_GOAL := help
.PHONY: help install lock verify-lock up down down-v seed token run test test-int e2e lint types build ci fmt demo layout schemas leak-demo benchmark red-team openapi

# --- Supply-chain safety -----------------------------------------------------
# Lockfiles (uv.lock, pnpm-lock.yaml) are the single source of truth and are
# committed. Every install/run below is FROZEN: it must match the lockfile or
# fail loudly. Versions never drift implicitly. To change a dependency you must
# run `make lock` explicitly, which is reviewable in the diff.
UV_CACHE_DIR ?= .uv-cache
UV_RUN := UV_CACHE_DIR=$(UV_CACHE_DIR) uv run --frozen $(if $(wildcard .env),--env-file .env,)

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install deps EXACTLY as locked (no drift, no resolution)
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv sync --frozen --all-packages
	pnpm install --frozen-lockfile

lock: ## Intentionally update lockfiles (review the diff before commit!)
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv lock
	pnpm install --lockfile-only

verify-lock: ## Fail if lockfiles are stale vs manifests (CI gate)
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv lock --check
	pnpm install --frozen-lockfile

up: ## Start the local stack (compose), wait until healthy
	docker compose up -d --wait

down: ## Stop the local stack (keeps volumes/data)
	docker compose down

down-v: ## DESTRUCTIVE: stop the stack AND delete all volumes (data loss!)
	docker compose down -v

seed: ## Enqueue + drain ingestion of the seed corpus (needs `make up`)
	$(UV_RUN) python scripts/seed.py

token: ## Mint a demo identity token, e.g. `make token SUB=sales@acme`
	@$(UV_RUN) python scripts/issue_token.py $(SUB)

run: ## Run the API locally (uvicorn, reload)
	$(UV_RUN) uvicorn contextguard.api.app:create_app --factory --reload --port 8000

test: ## Run the core test tier (no infra) + JS unit tests
	$(UV_RUN) pytest -m "not integration and not e2e"
	pnpm -r --if-present test

test-int: ## Run integration tier (needs `make up`)
	$(UV_RUN) pytest -m integration

e2e: ## Run the local demo smoke test (needs `make demo` or API on :8000)
	$(UV_RUN) python scripts/demo_smoke.py

lint: ## Lint Python + JS
	$(UV_RUN) ruff check .
	pnpm -r --if-present lint

types: ## Type-check Python (mypy) + JS (vue-tsc)
	$(UV_RUN) mypy
	pnpm -r --if-present typecheck

build: ## Build Python package artifacts + production web bundle
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv build --all-packages --out-dir dist/python
	pnpm --filter @contextguard/web build

ci: verify-lock lint types test build ## Run the full CI gate locally

fmt: ## Format Python + JS
	$(UV_RUN) ruff format .
	@command -v pnpm >/dev/null 2>&1 && pnpm -r --if-present format || true

demo: ## Run the demo flow
	$(UV_RUN) python scripts/demo.py

leak-demo: ## Print the before/after leak report (zero-infra, Public v0.1)
	$(UV_RUN) python scripts/leak_demo.py

benchmark: ## Regenerate BENCHMARK.md from the Public v0.1 scenarios (zero-infra)
	$(UV_RUN) python scripts/benchmark.py

red-team: ## Run the red-team corpus through the firewall and regenerate RED-TEAM.md (zero-infra)
	$(UV_RUN) python scripts/red_team.py

layout: ## Assert the monorepo layout matches ADR-003
	python3 scripts/check_layout.py

schemas: ## Regenerate committed JSON Schema snapshots from the contracts models
	$(UV_RUN) python scripts/gen_schemas.py

openapi: ## Regenerate the OpenAPI snapshot + typed TS client (contracts -> apps/web)
	$(UV_RUN) python scripts/dump_openapi.py
	pnpm --filter @contextguard/web run gen:api
