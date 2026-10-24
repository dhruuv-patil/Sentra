.PHONY: test eval eval-smoke lint format ci clean run run-dashboard

PYTHON := python3

test:
	$(PYTHON) -m pytest --cov=core --cov=app --cov=data --cov-fail-under=70

test-fuzz:
	$(PYTHON) -m pytest tests/test_fuzz_guards.py -v

eval:
	$(PYTHON) eval/run_eval.py

eval-smoke:
	$(PYTHON) eval/eval_smoke_test.py

lint:
	ruff check .
	mypy app core data

format:
	ruff format .
	ruff check --fix .

ci: lint test eval-smoke
	@echo "All CI quality gates passed successfully."

run:
	$(PYTHON) run_api.py

run-dashboard:
	$(PYTHON) run_dashboard.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage
