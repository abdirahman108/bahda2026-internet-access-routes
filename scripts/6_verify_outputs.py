"""Step 6: Check that your run reproduces 25 key numbers reported in the manuscript.

Run this script after 2_run_analysis.py and 3_model_family.py. From the repository's main folder, run:

    python3 scripts/6_verify_outputs.py

The script prints PASS or FAIL for each check. If any check fails, it exits with status 1.
"""
import json
import sys

import pandas as pd

import _paths  # noqa: F401  (puts lib/ on the import path)
from variables import OUT

TAB = OUT / "tables"
R = json.load(open(OUT / "results.json"))
t3 = pd.read_csv(TAB / "table3_full_model_rrr.csv")
ame = pd.read_csv(TAB / "table4_ame.csv")
fam = pd.read_csv(TAB / "model_family" / "table5_model_family.csv").set_index("model")
mc = {m["model"]: m for m in R["model_cmp"]}


def rrr(term, outcome):
    return t3[(t3.term == term) & (t3.outcome == outcome)].iloc[0]


def me(variable, level, outcome):
    return ame[(ame.variable == variable) & (ame.level.astype(str) == level) & (ame.outcome == outcome)].iloc[0]


# Each check: (what it is, value from your run, value in the manuscript, largest allowed difference)
CHECKS = [
    ("Analytical sample (households)", R["n"], 2707, 0),
    ("Design degrees of freedom", R["dfd"], 2701, 0),
    ("Weighted % no internet access", 100 * R["outcome"]["0"]["p"], 22.2, 0.05),
    ("Weighted % smartphone mobile data", 100 * R["outcome"]["1"]["p"], 33.6, 0.05),
    ("Weighted % feature-phone mobile data", 100 * R["outcome"]["2"]["p"], 20.6, 0.05),
    ("Weighted % home Wi-Fi/fibre", 100 * R["outcome"]["3"]["p"], 21.7, 0.05),
    ("Weighted % public Wi-Fi/cyber café", 100 * R["outcome"]["4"]["p"], 1.9, 0.05),
    ("Rao–Scott F, residence (Table 2)", R["bivariate"]["residence"]["stat"], 48.951, 0.001),
    ("Rao–Scott F, smartphone (Table 2)", R["bivariate"]["smartphone"]["stat"], 70.498, 0.001),
    ("Model 3 pseudo-log-likelihood (Table 3)", R["full_info"]["ll"], -2926.486, 0.001),
    ("Model 3 AIC (Table 3)", R["full_info"]["aic"], 6028.972, 0.001),
    ("Model 3 McFadden pseudo-R2 (Table 3)", R["full_info"]["r2_mcf"], 0.245, 0.0005),
    ("RRR peri-urban, home Wi-Fi/fibre (Table 3)", rrr("residence=2", 3).rrr, 0.04, 0.005),
    ("RRR rural, home Wi-Fi/fibre (Table 3)", rrr("residence=3", 3).rrr, 0.07, 0.005),
    ("RRR smartphone, smartphone data (Table 3)", rrr("smartphone=1", 1).rrr, 7.22, 0.005),
    ("RRR expenditure >=US$1,000, home Wi-Fi/fibre (Table 3)", rrr("monthly_expenditure=5", 3).rrr, 16.61, 0.005),
    ("AME no electricity on no access, points (Table 4)", 100 * me("electricity_source", "4", 0).ame, 21.6, 0.05),
    ("AME smartphone on no access, points (Table 4)", 100 * me("smartphone", "1", 0).ame, -23.6, 0.05),
    ("AME peri-urban on home Wi-Fi/fibre, points (Table 4)", 100 * me("residence", "2", 3).ame, -25.7, 0.05),
    ("Model 3 BIC, lowest BIC (Table 5)", mc["M3"]["bic"], 6548.488, 0.001),
    ("Model 4 (15 predictors) AIC, lowest AIC (Table 5)", mc["M4"]["aic"], 5835.574, 0.001),
    ("Unweighted multinomial logit log-likelihood (Table 5)", fam.loc["Multinomial logit", "ll"], -3194.513, 0.001),
    ("Unweighted multinomial logit AIC (Table 5)", fam.loc["Multinomial logit", "aic"], 6565.026, 0.001),
    ("Two-part nominal logit AIC (Table 5)", fam.loc["Two-part nominal logit", "aic"], 6568.035, 0.01),
    ("Two-part nominal probit AIC (Table 5)", fam.loc["Two-part nominal probit", "aic"], 6566.869, 0.01),
]

failed = 0
for name, got, want, tol in CHECKS:
    ok = abs(float(got) - want) <= tol
    failed += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {float(got):.4f} (manuscript {want})")
print(f"\n{len(CHECKS) - failed} of {len(CHECKS)} checks passed")
sys.exit(1 if failed else 0)
