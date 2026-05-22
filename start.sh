#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "============================================================"
echo " HirePipe - one-click demo"
echo "============================================================"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 not installed. macOS: brew install python3"
    exit 1
fi

if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

echo "Generating mock applications ..."
python scripts/seed_applications.py

echo "============================================================"
echo " Running HirePipe (5 applicants across all 4 scenarios)"
echo "============================================================"
python scripts/run_pipeline.py

echo "============================================================"
echo " Done. Per-applicant artifacts in data/output/"
echo "============================================================"
