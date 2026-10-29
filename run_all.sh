#!/usr/bin/env bash
# Runs steps 2 to 6 of the analysis and checks the results against the manuscript.
# To use it, from the repository's main folder, run:  bash run_all.sh
set -euo pipefail
cd "$(dirname "$0")"
test -f data/borama_internet_access.dta || {
  echo "Missing data/borama_internet_access.dta. See 'Reproduce the results' in README.md." >&2; exit 1; }
python3 scripts/2_run_analysis.py
python3 scripts/3_model_family.py
python3 scripts/4_excluded_households.py
python3 scripts/5_make_figures.py
python3 scripts/6_verify_outputs.py
