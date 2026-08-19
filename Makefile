# Instant Download Sorter — cross-platform Makefile
#
# Works on macOS (Xcode CLT / brew make) and Windows (Git Bash / MSYS2 / WSL,
# or `choco install make`). Recipes assume a POSIX shell, which GNU make uses
# on both platforms. The script itself is pure stdlib and runs anywhere.
#
# The Python interpreter is detected at runtime so `run`/`install` work whether
# the machine calls it python3 (macOS/Linux) or py/python (Windows).

.DEFAULT_GOAL := help

# Prefer the first interpreter that exists; fall back gracefully.
PY := $(shell command -v python3 >/dev/null 2>&1 && echo python3 || { command -v py >/dev/null 2>&1 && echo py || echo python; })

.PHONY: help run install

help: ## Show this help
	@echo "Instant Download Sorter — available targets:"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## ' Makefile | sed 's/^/  /; s/:[^#]*##/ /'
	@echo
	@echo "Requirements: make + Python 3. On Windows run make from Git Bash/"
	@echo "MSYS2/WSL (or 'choco install make' and use a POSIX shell)."

run: ## Run the sorter
	python3 src/InstantSorter.py || py src/InstantSorter.py || python src/InstantSorter.py

install: ## Install dependencies from requirements.txt (none currently)
	@if [ ! -f requirements.txt ]; then \
		echo "No requirements.txt — this project has no external dependencies (pure stdlib)."; \
	elif command -v python3 >/dev/null 2>&1; then \
		python3 -m pip install -r requirements.txt; \
	elif command -v py >/dev/null 2>&1; then \
		py -m pip install -r requirements.txt; \
	else \
		python -m pip install -r requirements.txt; \
	fi
