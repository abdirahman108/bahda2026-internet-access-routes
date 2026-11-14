"""Step 7 (optional): Put the R cross-check next to the Python results.

Run this script after 2_run_analysis.py and r_crosscheck.R. From the repository's main folder, run:

    python3 scripts/7_compare_r.py

It saves outputs/tables/tableS_software_agreement.csv: for every coefficient of the main model, the
Python and R estimates and standard errors and the differences between them. It also prints the largest
differences.
"""
import re

import pandas as pd

import _paths  # noqa: F401  (puts lib/ on the import path)
from variables import OUT

TAB = OUT / "tables"
py = pd.read_csv(TAB / "table3_full_model_rrr.csv")
r = pd.read_csv(TAB / "r_crosscheck_coefficients.csv")


def to_python_term(t):
    """Turn an R coefficient name such as 'residence2' into the Python name 'residence=2'."""
    if t == "(Intercept)":
        return "_cons"
    if t == "head_age10":
        return "head_age"
    m = re.fullmatch(r"(.*?)(\d+)", t)
    return f"{m.group(1)}={m.group(2)}" if m and m.group(1) != "" and not t.startswith("household_size") else t


r["term"] = r.r_term.map(to_python_term)
m = py.merge(r, on=["outcome", "term"], how="left")
m["diff_b"] = m.b_r - m.b
m["diff_se"] = m.se_r - m.se
m["ratio_se"] = m.se_r / m.se
out = m[["outcome", "term", "b", "b_r", "diff_b", "se", "se_r", "diff_se", "ratio_se", "separated"]]
out.to_csv(TAB / "tableS_software_agreement.csv", index=False)

ok = out[~out.separated]
print(f"coefficients matched: {ok.b_r.notna().sum()} of {len(ok)} estimable")
print(f"largest absolute difference in coefficients: {ok.diff_b.abs().max():.6f}")
print(f"largest absolute difference in standard errors: {ok.diff_se.abs().max():.6f}")
print(f"standard-error ratio (R / Python): {ok.ratio_se.min():.4f} to {ok.ratio_se.max():.4f}")
if "r_crosscheck_outcome.csv" in [p.name for p in TAB.iterdir()]:
    o = pd.read_csv(TAB / "outcome_distribution_overall.csv").merge(
        pd.read_csv(TAB / "r_crosscheck_outcome.csv"), on="level")
    print(f"largest difference in weighted outcome shares: {(o.p - o.p_r).abs().max():.6f}")
