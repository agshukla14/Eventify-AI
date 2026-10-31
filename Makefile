.PHONY: dev test eval seed build clean

dev:
	@echo "Starting Celebration Planner (FastAPI + React UI)..."
	@python start_app.py

test:
	@echo "Running Pytest and Playwright Smoke Suite..."
	@pytest backend/tests

eval:
	@echo "Running Complete Evaluation Suite (42 scenarios)..."
	@python evals/run_evals.py

seed:
	@echo "Seeding demo events..."
	@python backend/app/seed_data.py

build:
	@echo "Building frontend static assets..."
	@cd frontend && npm run build
