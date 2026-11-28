# Variables
SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c
UV = uv
VENV_DEV = .venv
VENV_BUILD = .venv-build
BUILD_DIR = build
EXE = $(BUILD_DIR)/pdf-fmt
LOG_FILE = nuitka-build.log

.PHONY: help setup test test-e2e lint check run compile run-compiled act clean requirements release docs-check complexity sbom

# Default target: show help
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  setup         Sync .venv and update requirements.txt"
	@echo "  install       Install project locally using uv"
	@echo "  sync          setup + install"
	@echo "  test          Run unit tests using .venv"
	@echo "  test-e2e      Run end-to-end tests, including the compiled binary when built"
	@echo "  lint          Run Ruff checks"
	@echo "  check         Run lint, tests, compile, E2E, docs and complexity gates"
	@echo "  docs-check    Reject em dashes in hand-written Markdown docs"
	@echo "  complexity    Run the adacovex 10% LOC gate on source files"
	@echo "  sbom          Generate sbom.json with the sibling adacovex binary"
	@echo "  run           Run pdf-fmt.py using .venv. Pass ARGS with make run ARGS='--version'"
	@echo "  compile       Build standalone binary using .venv-build"
	@echo "  run-compiled  Execute the compiled binary"
	@echo "  clean         Remove venvs, build artifacts, and logs"
	@echo "  release       Release new version with helper shell script."

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

test-e2e:
	$(UV) run python -m unittest discover -sv tests -p 'test_e2e*.py'

lint:
	$(UV) run ruff check

check: lint test compile test-e2e docs-check complexity

docs-check:
	$(UV) run python tools/check_docs.py

complexity:
	../adacovex/bin/adacovex complexity --target=. --excludes=md,rst \
		--skip-path=.venv --skip-path=.venv-build --skip-path=.headroom \
		--skip-path=.lccst --skip-path=.ruff_cache --skip-path=build \
		--skip-path=sbom.json

sbom:
	../adacovex/bin/adacovex sbom --target=. --format=cyclonedx-json --out=sbom.json

install:
	uv tool install --editable .

sync:
	$(MAKE) setup
	$(MAKE) install

release:
	@./scripts/version.sh

clean:
	rm -rf $(VENV_DEV) $(VENV_BUILD) $(BUILD_DIR) $(LOG_FILE)
	find . -type d -name "__pycache__" -exec rm -rf {} +

ARGS ?=

run:
	$(UV) run python pdf-fmt.py $(ARGS)

compile:
	@echo "Extracting version from pyproject.toml..."
	$(eval PKG_VERSION=$(shell grep -m 1 'version =' pyproject.toml | cut -d '"' -f 2))
	@echo "Building version $(PKG_VERSION)..."
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
		--include-package-data=zhconv \
		--python-flag=no_docstrings \
		--warn-unusual-code \
		--output-file=pdf-fmt \
		--output-dir=$(BUILD_DIR) \
		--product-version=$(PKG_VERSION) \
		--file-version=$(PKG_VERSION) \
		--company-name="bladeacer" \
		--copyright="Copyright (C) 2025 bladeacer. Licensed under GPLv3." \
		--product-name="pdf-fmt" \
		build.py 2>&1 | tee $(LOG_FILE)

run-compiled: compile
	@if [ -f $(EXE) ]; then \
		echo "Running compiled binary..."; \
		./$(EXE) $(ARGS); \
	else \
		echo "Error: Binary not found. Run 'make compile' first."; \
		exit 1; \
	fi
