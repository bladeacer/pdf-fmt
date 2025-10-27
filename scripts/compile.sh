#!/bin/sh
set -e

if [ -d "build" ]; then
    echo "Cleaning up existing 'build' directory..." | tee -a nuitka-build.log
    rm -rf build
fi

if [ -d ".venv-build" ]; then
    echo "Cleaning up existing '.venv-build' directory..." | tee -a nuitka-build.log
    rm -rf .venv-build
fi

python -m venv .venv-build
source ./.venv-build/bin/activate
pip install --upgrade pip
python -m pip install uv
uv pip install -r requirements-ci.txt
uv pip install nuitka 

python -m nuitka \
    --jobs=2 \
    --low-memory \
    --show-memory \
    --show-scons \
    --mode=app \
    --python-flag=no_docstrings \
    --include-package=core,parser \
    --warn-unusual-code \
    --output-file=pdf-fmt \
    --output-dir=build \
    --company-name="bladeacer" \
    --copyright="Copyright (C) 2025 bladeacer. Licensed under GPLv3." \
    --product-name="pdf-fmt" \
    --output-dir=build \
    build.py 2>&1 | tee nuitka-build.log 
