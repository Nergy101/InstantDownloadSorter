# Instant Download Sorter -- cross-platform Makefile
#
# macOS / Linux: plain GNU make + python3 (curses is built in).
# Windows:       GNU make from Git Bash, MSYS2, or WSL, or `choco install make`.
#                The recipes also work if your make shells out to cmd.exe:
#                they fall back across python3 / py / python and delegate all
#                logic to make.py, which needs no POSIX shell tools.
#
# The app itself is pure stdlib, but native Windows Python lacks the `curses`
# module, so `make install` adds `windows-curses` there automatically.

.DEFAULT_GOAL := help

.PHONY: help run install

help: ## Show this help
	@python3 make.py help || py make.py help || python make.py help

run: ## Run the sorter
	@python3 make.py run || py make.py run || python make.py run

install: ## Install dependencies (windows-curses on Windows; requirements.txt if present)
	@python3 make.py install || py make.py install || python make.py install
