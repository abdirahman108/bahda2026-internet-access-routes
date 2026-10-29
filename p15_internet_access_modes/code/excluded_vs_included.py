"""Profile of the 189 households excluded for expenditure "Prefer not to say".

The analytical extract holds only the 2,707 complete records. The BAHDA-2026 Atlas publishes
full-sample (N = 2,896) unweighted and weighted counts for every item used here, so the excluded
households' distribution is the Atlas count minus the extract count. Unweighted counts are exact;
weighted counts carry the Atlas's rounding to 0.1. Because the weight is constant within stratum,
the excluded households' weights follow from their stratum counts.

Run:  python3 excluded_vs_included.py      (from this folder)
"""
import json

import numpy as np
import pandas as pd
from scipy import stats

from setup_data import load, OUTCOME, OUT

TAB = OUT / "tables"
df, vl = load()
W = df["survey_weight"]

# Atlas Table 2.15: consented households by stratum (stratum codes as in the extract)
ATLAS_STRATUM = {1: 602, 2: 615, 3: 627, 4: 616, 5: 217, 6: 219}

# Atlas full-sample item tables: {extract code: (unweighted n, weighted n)}
ATLAS = {
    (OUTCOME, "4.1.6"): {0: (312, 653.4), 1: (853, 961.3), 2: (630, 601.5), 3: (1010, 622.7), 4: (91, 57.0)},
    ("head_sex", "1.1.4"): {1: (1512, 1462.8), 2: (1384, 1433.2)},
    ("head_education", "1.1.8"): {0: (615, 847.2), 1: (640, 712.4), 2: (473, 464.0), 3: (84, 96.8),
                                  4: (1084, 775.6)},
    ("head_employment", "1.4.1"): {1: (1169, 1259.8), 2: (815, 641.3), 3: (432, 595.5), 4: (480, 399.3)},
    ("electricity_source", "4.4.1"): {1: (2139, 1647.3), 2: (418, 669.2), 3: (150, 178.6), 4: (189, 400.9)},
    ("smartphone", "4.1.2"): {0: (448, 653.5), 1: (2448, 2242.5)},
    ("youth_vocational_training", "1.3.1"): {0: (1332, 1624.0), 1: (1564, 1272.0)},
}
# Atlas Tables 1.1.5 and 1.1.7: full-sample means (unweighted, weighted)
ATLAS_MEANS = {"head_age": (43.956, 44.236), "household_size": (8.121, 8.021)}
N_FULL, N_EXC = 2896, 189

LABELS = {OUTCOME: "Main route to the internet", "residence": "Residence (stratum)",
          "head_sex": "Sex of household head", "head_education": "Education of household head",
          "head_employment": "Employment of household head", "electricity_source": "Electricity source",
          "smartphone": "Household owns a smartphone",
          "youth_vocational_training": "Youth vocational training"}


def calibrated_weights(data, margins=("sampling_stratum", OUTCOME, "head_employment", "electricity_source"),
                       iters=200):
    """Rake the extract's weights so that its weighted margins match the full 2,896-household sample.

    Targets are the Atlas full-sample weighted counts (stratum targets are consented households times the
    stratum weight), so the calibrated weights stand in for the excluded households along these margins.
    """
    w = data["survey_weight"].to_numpy(dtype=float).copy()
    ws = data.groupby("sampling_stratum")["survey_weight"].first()
    targets = {"sampling_stratum": {s: ATLAS_STRATUM[s] * ws[s] for s in ATLAS_STRATUM}}
    for (var, _), counts in ATLAS.items():
        if var in margins:
            targets[var] = {k: v[1] for k, v in counts.items()}
    for _ in range(iters):
        for var in margins:
            x = data[var].to_numpy()
            for k, t in targets[var].items():
                m = x == k
                w[m] *= t / w[m].sum()
    return w * len(w) / w.sum()


OUTLAB = {0: "No internet access", 1: "Smartphone data", 2: "Feature-phone data", 3: "Home Wi-Fi/fibre",
          4: "Public Wi-Fi/cyber café"}

def main():
    rows, tests = [], []

    # stratum: excluded counts, and the stratum weight each excluded household carries
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

    # continuous: excluded mean from the full-sample and extract means
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
