#!/usr/bin/env bash
# Run the full Paper 15 analysis and check the results against the manuscript.
# Usage (from p15_internet_access_modes/code):  bash run_all.sh
set -euo pipefail
cd "$(dirname "$0")"
test -f ../data/p15_internet_access_modes_clean.dta || {
  echo "Missing ../data/p15_internet_access_modes_clean.dta (see REPRODUCE.md, step 2)" >&2; exit 1; }
python3 run_analysis.py
python3 model_family.py
python3 make_figures.py
python3 verify_outputs.py
