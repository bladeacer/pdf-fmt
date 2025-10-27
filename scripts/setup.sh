#!/bin/sh
set -e
if [ -d ".venv" ]; then
    echo "Cleaning up existing '.venv' directory..." | tee -a nuitka-setup.log
    rm -rf .venv
fi

python -m venv .venv
. ./.venv/bin/activate
pip install --upgrade pip
python -m pip install uv
uv pip install -r requirements-ci.txt
