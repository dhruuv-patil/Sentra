.PHONY: test eval lint clean run run-dashboard

PYTHON := python3

test:
	$(PYTHON) -m pytest

eval:
	$(PYTHON) eval/run_eval.py

lint:
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check .; \
	else \
		$(PYTHON) -m py_compile app/**/*.py core/**/*.py data/**/*.py tests/**/*.py eval/**/*.py; \
		echo "Syntax check passed across all packages."; \
	fi

run:
	$(PYTHON) run_api.py

run-dashboard:
	$(PYTHON) run_dashboard.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
