.DEFAULT_GOAL := help

.PHONY: help run install

help: ## Show this help
	@echo "Instant Download Sorter — available targets:"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sed 's/^/  /; s/:[^#]*##/ /'

run: ## Run the sorter
	python3 src/InstantSorter.py || py src/InstantSorter.py || python src/InstantSorter.py

install: ## Install dependencies (from requirements.txt, if present)
	@if [ -f requirements.txt ]; then \
		python3 -m pip install -r requirements.txt; \
	else \
		echo "No requirements.txt — this project has no external dependencies (pure stdlib)."; \
	fi
