# FitVision developer shortcuts.
# Windows users can run these from Git Bash / WSL, or copy the commands directly.

PYTHON ?= python
NPM ?= npm
BACKEND_ENV = DB_ENGINE=sqlite CACHE_BACKEND=locmem

.PHONY: help install install-backend install-frontend migrate seed seed-history seed-population \
        backend frontend test test-backend check lint format docker-up docker-down

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: install-backend install-frontend ## Install backend and frontend dependencies

install-backend: ## Install Python dependencies
	cd backend && $(PYTHON) -m pip install -r requirements-dev.txt

install-frontend: ## Install frontend dependencies from the lockfile
	cd frontend && $(NPM) ci

migrate: ## Apply database migrations
	cd backend && $(PYTHON) manage.py migrate

seed: ## Import demo exercises and training plan when the database is empty
	cd backend && $(PYTHON) manage.py seed_demo

seed-history: ## Generate reproducible synthetic training history for the demo user
	cd backend && $(PYTHON) manage.py seed_demo_history --create-user

seed-population: ## Generate a balanced multi-user dataset for the recommender
	cd backend && $(PYTHON) manage.py seed_population --users 12 --weeks 6

backend: ## Import demo data, then run the Django development server
	cd backend && $(PYTHON) manage.py seed_demo
	cd backend && $(PYTHON) manage.py runserver

frontend: ## Run the Vite development server
	cd frontend && $(NPM) run dev

test: test-backend lint ## Run backend tests and frontend checks

test-backend: ## Run Django tests with SQLite + LocMem
	cd backend && $(BACKEND_ENV) $(PYTHON) manage.py test

check: ## Run Django system checks and frontend type-check
	cd backend && $(BACKEND_ENV) $(PYTHON) manage.py check
	cd frontend && $(NPM) run type-check

lint: ## Lint and type-check the frontend
	cd frontend && $(NPM) run lint
	cd frontend && $(NPM) run type-check

format: ## Format the frontend and backend
	cd frontend && $(NPM) run format
	cd backend && $(PYTHON) -m black . && $(PYTHON) -m isort .

docker-up: ## Build and start the full Docker Compose stack
	docker compose up --build

docker-down: ## Stop the Docker Compose stack
	docker compose down
