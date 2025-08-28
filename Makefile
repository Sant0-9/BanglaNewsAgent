.PHONY: help install db-up db-down db-migrate db-backfill dev api clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install Python dependencies
	pip install -r requirements.txt

db-up: ## Start PostgreSQL database with Docker
	docker-compose -f docker-compose.db.yml up -d

db-down: ## Stop PostgreSQL database
	docker-compose -f docker-compose.db.yml down

db-migrate: ## Run database migrations
	alembic upgrade head

db-migrate-create: ## Create a new migration (run after model changes)
	alembic revision --autogenerate -m "$(MSG)"

db-backfill: ## Backfill existing JSON cache to database
	python scripts/migrate_json_to_db.py

dev: db-up install db-migrate ## Set up development environment
	@echo "Development environment ready!"
	@echo "Run 'make api' to start the API server"

api: ## Start the API server
	uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

test-ingest: ## Test the ingestion pipeline
	python -c "from services.ingest.rss import gather_candidates; print('Testing ingestion...'); articles = gather_candidates(max_items=10); print(f'Ingested {len(articles)} articles')"

clean: ## Clean up cache files and logs
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf *.egg-info/

# Database utility commands
db-reset: ## Reset database (WARNING: destroys all data)
	@echo "This will destroy all data. Are you sure? [y/N]" && read ans && [ $${ans:-N} = y ]
	docker-compose -f docker-compose.db.yml down -v
	docker-compose -f docker-compose.db.yml up -d
	sleep 5
	alembic upgrade head

db-shell: ## Connect to database shell
	psql -h localhost -U postgres -d khobor

# Development shortcuts
run-migration: ## Run the JSON to DB migration script
	python scripts/migrate_json_to_db.py

check-db: ## Check database connection and show stats
	python -c "from packages.db.repo import init_db, get_recent_articles; init_db(); articles = get_recent_articles(1); print(f'Database connected. Sample articles: {len(articles)}')"