.DEFAULT_GOAL := help
VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
BROWSER ?= chrome

.PHONY: help install install-browser test run-example clean build

help: ## List targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-16s %s\n", $$1, $$2}'

install: ## Create venv and install (with dev extras)
	@python3 -m venv $(VENV)
	@$(PIP) install --quiet --upgrade pip
	@$(PIP) install --quiet -e ".[dev]"
	@echo "installed into $(VENV). Uses system Chrome/Edge by default."

install-browser: ## Install Playwright Chromium browser (optional, only if no system Chrome/Edge)
	@$(PY) -m playwright install chromium

test: ## Run tests
	@$(PY) -m pytest -q

run-example: ## Build the report example PDF (uses system Chrome)
	@$(PY) -m pdfgen build --template report --data examples/report/data/data.json --output out/report.pdf --browser $(BROWSER)

clean: ## Remove venv, build artifacts and outputs
	@rm -rf $(VENV) out build src/*.egg-info .pytest_cache
