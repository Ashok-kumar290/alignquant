#!/usr/bin/env bash
# AlignQuant environment setup
set -euo pipefail
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "Env ready. source .venv/bin/activate to use."
