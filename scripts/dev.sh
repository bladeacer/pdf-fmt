#!/bin/sh
set -e
source ./.venv/bin/activate
python -m pip install uv
uv pip install -r requirements.txt
uv pip install nuitka 

python -m nuitka \
    --module-name=pdf_fmt \
    --standalone \
    --include-package=parser,core \
    --output-dir=./build \
    --assume-yes-for-downloads \
    --onefile \
    build.py
