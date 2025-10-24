#!/bin/sh
set -e
source ./.venv/bin/activate
python -m pip install uv
uv pip install -r requirements.txt
uv pip install nuitka 

python -m nuitka --onefile --standalone --output-dir=dist pdf-fmt.py
