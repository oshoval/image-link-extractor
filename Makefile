.PHONY: lint fmt test e2e check clean

lint:  ## Run linter checks
	ruff check .
	ruff format --check .

fmt:  ## Auto-format code
	ruff check --fix .
	ruff format .

test:  ## Run unit tests
	python -m pytest tests/ -v

e2e:  ## Run e2e test against sample image
	python extract_links.py examples/sample.png

check: lint test e2e  ## Run all checks (lint + unit tests + e2e)
	@echo "All checks passed."

clean:  ## Remove build/cache artifacts
	rm -rf __pycache__ .pytest_cache .ruff_cache dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
