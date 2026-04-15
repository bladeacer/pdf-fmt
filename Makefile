# Variables
UV = uv
VENV_DEV = .venv
VENV_BUILD = .venv-build
BUILD_DIR = build
EXE = $(BUILD_DIR)/pdf-fmt
LOG_FILE = nuitka-build.log

.PHONY: help setup test run compile run-compiled act clean requirements

# Default target: show help
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  setup         Sync .venv and update requirements.txt"
	@echo "  install       Install project locally using uv"
	@echo "  test          Run unit tests using .venv"
	@echo "  run           Run pdf-fmt.py using .venv"
	@echo "  compile       Build standalone binary using .venv-build"
	@echo "  run-compiled  Execute the compiled binary"
	@echo "  clean         Remove venvs, build artifacts, and logs"

setup:
	@echo "Syncing development environment..."
	$(UV) sync
	@$(MAKE) requirements

requirements:
	@echo "Updating requirements.txt..."
	$(UV) export --format requirements-txt --no-hashes --no-emit-project | sed 's/==.*//' > requirements.txt

# Run Tests (Does NOT force a requirements update)
test:
	$(UV) run python -m unittest discover -sv tests

run:
	$(UV) run python pdf-fmt.py

compile:
	@echo "Cleaning up previous build artifacts..."
	rm -rf $(BUILD_DIR) $(VENV_BUILD)
	@echo "Syncing build environment..."
	UV_PROJECT_ENVIRONMENT=$(VENV_BUILD) $(UV) sync --group build
	@echo "Starting Nuitka compilation..."
	UV_PROJECT_ENVIRONMENT=$(VENV_BUILD) $(UV) run python -m nuitka \
		--jobs=2 \
		--low-memory \
		--show-memory \
		--show-scons \
		--mode=app \
		--noinclude-setuptools-mode=nofollow \
		--noinclude-unittest-mode=nofollow \
		--noinclude-pytest-mode=nofollow \
		--python-flag=no_docstrings \
		--warn-unusual-code \
		--output-file=pdf-fmt \
		--output-dir=$(BUILD_DIR) \
		--company-name="bladeacer" \
		--copyright="Copyright (C) 2025 bladeacer. Licensed under GPLv3." \
		--product-name="pdf-fmt" \
		build.py 2>&1 | tee $(LOG_FILE)

install:
	uv tool install --editable .

run-compiled: compile
	@if [ -f $(EXE) ]; then \
		echo "Running compiled binary..."; \
		./$(EXE); \
	else \
		echo "Error: Binary not found. Run 'make compile' first."; \
		exit 1; \
	fi

clean:
	rm -rf $(VENV_DEV) $(VENV_BUILD) $(BUILD_DIR) $(LOG_FILE)
	find . -type d -name "__pycache__" -exec rm -rf {} +
