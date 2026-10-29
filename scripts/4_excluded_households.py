"""Step 4: Describe the 189 households left out because they chose "Prefer not to say" about spending.

The analysis file contains only the 2,707 households with complete answers. The BAHDA-2026 Atlas
publishes counts for all 2,896 households, with and without weights, for every question used here.
So, for each answer, the number of left-out households is the Atlas count minus the analysis file's
count.

- Counts without weights are exact.
- Weighted counts carry the Atlas's rounding to one decimal place.
- Every household in a stratum has the same weight, so the left-out households' weights follow from
  how many of them are in each stratum.

The script saves Supplementary Table S1b and outputs/excluded_profile.json.

To run this script, from the repository's main folder, run:

    python3 scripts/4_excluded_households.py
"""
import json

import numpy as np
import pandas as pd
from scipy import stats

import _paths  # noqa: F401  (puts lib/ on the import path)
from variables import load, OUTCOME, OUT
from atlas_margins import ATLAS, ATLAS_MEANS, ATLAS_STRATUM, N_FULL, N_EXC

TAB = OUT / "tables"

LABELS = {OUTCOME: "Main route to the internet", "residence": "Residence (stratum)",
          "head_sex": "Sex of household head", "head_education": "Education of household head",
          "head_employment": "Employment of household head", "electricity_source": "Electricity source",
          "smartphone": "Household owns a smartphone",
          "youth_vocational_training": "Youth vocational training"}


OUTLAB = {0: "No internet access", 1: "Smartphone data", 2: "Feature-phone data", 3: "Home Wi-Fi/fibre",
          4: "Public Wi-Fi/cyber café"}

def main():
    df, vl = load()
    W = df["survey_weight"]
    rows, tests = [], []

    # Left-out households in each stratum, and the weight that each of them carries
    inc_s = df.groupby("sampling_stratum").size()
    w_s = df.groupby("sampling_stratum")["survey_weight"].first()
    exc_s = pd.Series(ATLAS_STRATUM) - inc_s
    assert exc_s.sum() == N_EXC and (exc_s >= 0).all()
    res_of = {1: 1, 2: 1, 3: 1, 4: 1, 5: 2, 6: 3}
    inc_r = df.groupby("residence").size()
    inc_rw = df.groupby("residence")["survey_weight"].sum()
    exc_r = exc_s.groupby(lambda s: res_of[s]).sum()
    exc_rw = (exc_s * w_s).groupby(lambda s: res_of[s]).sum()
    for r, lab in {1: "Urban", 2: "Peri-urban", 3: "Rural"}.items():
        rows.append(dict(variable="residence", label=LABELS["residence"], level=lab, inc_n=int(inc_r[r]),
                         exc_n=int(exc_r[r]), inc_wpct=100 * inc_rw[r] / inc_rw.sum(),
                         exc_wpct=100 * exc_rw[r] / exc_rw.sum()))
    ct = np.array([[inc_s[s] for s in ATLAS_STRATUM], [exc_s[s] for s in ATLAS_STRATUM]])
    chi = stats.chi2_contingency(ct)
    tests.append(dict(variable="residence", source="2.15", chi2=chi[0], df=chi[2], p=chi[1]))

    for (var, table), counts in ATLAS.items():
        inc_u = df.groupby(var).size()
        inc_w = df.groupby(var)["survey_weight"].sum()
        exc_u = {k: v[0] - int(inc_u.get(k, 0)) for k, v in counts.items()}
        exc_w = {k: max(v[1] - float(inc_w.get(k, 0.0)), 0.0) for k, v in counts.items()}
        assert sum(exc_u.values()) == N_EXC and min(exc_u.values()) >= 0, (var, exc_u)
        tw = sum(exc_w.values())
        for k in counts:
            lab = OUTLAB[k] if var == OUTCOME else vl.get(var, {}).get(k, str(k))
            rows.append(dict(variable=var, label=LABELS[var], level=lab, inc_n=int(inc_u.get(k, 0)),
                             exc_n=exc_u[k], inc_wpct=100 * inc_w.get(k, 0.0) / inc_w.sum(),
                             exc_wpct=100 * exc_w[k] / tw))
        ct = np.array([[int(inc_u.get(k, 0)) for k in counts], [exc_u[k] for k in counts]])
        chi = stats.chi2_contingency(ct)
        tests.append(dict(variable=var, source=table, chi2=chi[0], df=chi[2], p=chi[1]))

    # Age and household size: work out the left-out households' average from the two published averages
    for var, (mu_u, mu_w) in ATLAS_MEANS.items():
        exc_mean = (N_FULL * mu_u - len(df) * df[var].mean()) / N_EXC
        wsum_exc = float((exc_s * w_s).sum())
        exc_wmean = (N_FULL * mu_w - (W * df[var]).sum()) / wsum_exc   # full weights sum to 2,896
        rows.append(dict(variable=var, label=var, level="mean", inc_n=len(df), exc_n=N_EXC,
                         inc_mean=df[var].mean(), exc_mean=exc_mean,
                         inc_wmean=(W * df[var]).sum() / W.sum(), exc_wmean=exc_wmean))

    out = pd.DataFrame(rows)
    out.to_csv(TAB / "tableS1b_excluded_vs_included.csv", index=False)
    tests = pd.DataFrame(tests)
    tests.to_csv(TAB / "tableS1b_tests.csv", index=False)
    summary = dict(excluded_by_stratum={int(k): int(v) for k, v in exc_s.items()},
                   excluded_weight_total=float((exc_s * w_s).sum()),
                   tests=tests.set_index("variable").to_dict("index"))
    with open(OUT / "excluded_profile.json", "w") as f:
        json.dump(summary, f, indent=1, default=float)
    pd.set_option("display.width", 200)
    print(out.round(1).to_string())
    print(tests.round(4).to_string())
    print(summary["excluded_by_stratum"], round(summary["excluded_weight_total"], 1))


if __name__ == "__main__":
    main()
