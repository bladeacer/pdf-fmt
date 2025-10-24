#!/bin/sh
set -e
git clone --depth 1 https://github.com/bladeacer/pdf-fmt
python -m venv .venv
source ./.venv/bin/activate
python -m pip install uv

uv pip install -r requirements.txt
