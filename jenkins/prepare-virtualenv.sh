#!/bin/bash
set -xe -o pipefail

VENV="$1"

python3.7 -m venv --clear "${VENV}"
source "${VENV}/bin/activate"

pip install -r requirements.txt
