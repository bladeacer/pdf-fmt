#!/bin/sh
set -e

printf "
This script will install the 'pdf-fmt' command-line tool.

It will perform the following actions in the current directory:
1. Clone the 'pdf-fmt' repository from GitHub.
2. Change into the new 'pdf-fmt' directory.
3. Create a Python virtual environment named '.venv'.
4. Install the 'uv' package manager and all required Python dependencies (like PyMuPDF).

Do you want to proceed with the installation? (y/N): "

read CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Installation cancelled by the user."
    exit 0
fi
# --------------------------

echo "Starting installation..."

git clone --depth 1 https://github.com/bladeacer/pdf-fmt

cd pdf-fmt

python -m venv .venv
. ./.venv/bin/activate

python -m pip install uv
uv pip install -r requirements-ci.txt

echo ""
echo "Installation complete!"
echo "The virtual environment is now active."
echo "To run pdf-fmt later, navigate to the 'pdf-fmt' directory and run: source ./.venv/bin/activate"
echo "Then execute: pdf-fmt <file.pdf>"
