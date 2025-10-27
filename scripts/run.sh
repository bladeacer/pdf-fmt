#!/bin/sh
set -e

source ./.venv-build/bin/activate

python -m nuitka \
    --jobs=2 \
    --low-memory \
    --show-memory \
    --show-scons \
    --report=on \
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
