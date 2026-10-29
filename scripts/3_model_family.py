"""Unweighted model family for the nominal outcome (Supplementary Table S5).

Fits, on the ten selected predictors (age and household size in raw
units, lowest code of each categorical predictor as reference):
  1. multinomial logit (maximum likelihood)
  2-4. ridge, lasso and elastic-net multinomial logit (10-fold CV deviance)
  5. baseline-category logit with an alternative baseline (smartphone data)
  6-7. two-part nominal logit / probit: part 1 = home Wi-Fi/fibre vs any other
       outcome (logit or probit), part 2 = multinomial logit among the rest
It also writes the outcome-scale scan, unweighted bivariate screening
(Pearson chi-square, one-way ANOVA), indicator-level VIF, the multinomial
coefficient table and average predicted contrasts.

These unweighted fits are a comparison set only; inference in the paper uses
the survey-weighted model in 2_run_analysis.py.

Run:  python3 scripts/3_model_family.py      (from the repository root)
"""
import json
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import log_loss

import _paths  # noqa: F401  (puts lib/ on the import path)
from variables import load, OUTCOME, OUT_LABELS, CATS, CONTS, PRIMARY, OUT
from svy import SvyMlogit

warnings.filterwarnings("ignore")
TAB = OUT / "tables" / "model_family"
TAB.mkdir(parents=True, exist_ok=True)
R = {}

df, vl = load()
y = df[OUTCOME].astype(int).to_numpy()
n = len(df)
one = np.ones(n)
H, PSU = df["sampling_stratum"].to_numpy(), df["psu_hh"].to_numpy()
CAT = [c for c in CATS if c[0] in PRIMARY]
CON = [c for c in CONTS if c[0] in PRIMARY]


def design_lowref(d):
    """Dummies with the lowest code as reference, continuous terms unscaled."""
    cols = {}
    for name, label, ref, levels in CAT:
        for lv in sorted(levels)[1:]:
            cols[f"{name}={lv}"] = (d[name] == lv).astype(float)
    for name, label, scale in CON:
        cols[name] = d[name].astype(float)
    return pd.DataFrame(cols, index=d.index)


X = design_lowref(df)

# ---------------------------------------------------------------- Table 1
t1 = []
for lv, c in pd.Series(y).value_counts().sort_index().items():
    t1.append(dict(variable=OUTCOME, category=OUT_LABELS[lv], n=int(c), pct=100 * c / n))
for name, label, ref, levels in CAT:
    for lv in sorted(levels):
        c = int((df[name] == lv).sum())
        t1.append(dict(variable=name, category=vl[name].get(lv, lv), n=c, pct=100 * c / n))
for name, label, scale in CON:
    t1.append(dict(variable=name, category="mean (SD)", n=n, mean=df[name].mean(), sd=df[name].std()))
pd.DataFrame(t1).to_csv(TAB / "table1_descriptives_unweighted.csv", index=False)

# ---------------------------------------------------------------- Table 2: outcome-scale scan
vc = pd.Series(y).value_counts()
R["scan"] = dict(n=n, categories=int(vc.size), largest=OUT_LABELS[int(vc.idxmax())],
                 largest_pct=float(100 * vc.max() / n),
                 dominant_over_50=bool(vc.max() / n > 0.5))

# ---------------------------------------------------------------- Table 3: bivariate screening
biv = []
for name, label, ref, levels in CAT:
    chi2, p, dof, _ = stats.chi2_contingency(pd.crosstab(df[name], y), correction=False)
    biv.append(dict(variable=name, test="Pearson chi-square", stat=chi2, df=f"{dof}", p=p))
for name, label, scale in CON:
    F, p = stats.f_oneway(*[df.loc[y == k, name] for k in sorted(np.unique(y))])
    biv.append(dict(variable=name, test="One-way ANOVA", stat=F, df=f"4, {n - 5}", p=p))
biv = pd.DataFrame(biv)
biv.to_csv(TAB / "table3_bivariate_unweighted.csv", index=False)
R["bivariate"] = biv.set_index("variable")[["stat", "p"]].to_dict("index")

# ---------------------------------------------------------------- Table 4: VIF per indicator
A = X.to_numpy()
vif = []
for j, c in enumerate(X.columns):
    Z = np.column_stack([one, np.delete(A, j, 1)])
    e = A[:, j] - Z @ np.linalg.lstsq(Z, A[:, j], rcond=None)[0]
    vif.append(dict(variable=c.split("=")[0], vif=1 / (e @ e / ((A[:, j] - A[:, j].mean()) ** 2).sum())))
vif = pd.DataFrame(vif).groupby("variable").vif.agg(df="size", max_vif="max", mean_vif="mean").reset_index()
vif["tolerance"] = 1 / vif.max_vif
vif.to_csv(TAB / "table4_vif.csv", index=False)

# ---------------------------------------------------------------- Table 5: model family
def ic(ll, k, nobs=n):
    return dict(ll=ll, k=k, aic=-2 * ll + 2 * k, bic=-2 * ll + np.log(nobs) * k)


fam = []
mlog = SvyMlogit(y, X, one, H, PSU).fit()
fam.append(dict(model="Multinomial logit", **ic(mlog.ll, mlog.k)))

# penalised multinomial models: standardised predictors, 10-fold CV over a
# penalty grid, multinomial deviance (2 x mean log-loss) at the best penalty
Xz = (A - A.mean(0)) / A.std(0)
skf = StratifiedKFold(n_splits=10, shuffle=True, random_state=2026)
grid = np.logspace(-3, 2, 15)
for nm, sp in [("Ridge multinomial", dict(penalty="l2", solver="lbfgs")),
               ("Lasso multinomial", dict(penalty="l1", solver="saga")),
               ("Elastic-net multinomial", dict(penalty="elasticnet", l1_ratio=0.5, solver="saga"))]:
    best = None
    for C in grid:
        dev = []
        for tr, te in skf.split(Xz, y):
            clf = LogisticRegression(C=C, max_iter=5000, **sp).fit(Xz[tr], y[tr])
            dev.append(2 * log_loss(y[te], clf.predict_proba(Xz[te]), labels=[0, 1, 2, 3, 4]))
        if best is None or np.mean(dev) < best[1]:
            best = (C, np.mean(dev))
    fam.append(dict(model=nm, cv_deviance=best[1], C=best[0]))

alt = SvyMlogit(y, X, one, H, PSU, base=1).fit()
fam.append(dict(model="Baseline-category logit, alternative baseline (smartphone data)", **ic(alt.ll, alt.k)))

# two-part nominal models with home Wi-Fi/fibre (largest category) as part-1 split
Xc = sm.add_constant(X)
z = (y == 3).astype(int)
rest = y != 3
part2 = SvyMlogit(y[rest], X[rest], one[rest], H[rest], PSU[rest]).fit()
for nm, fam1 in [("Two-part nominal logit", sm.Logit), ("Two-part nominal probit", sm.Probit)]:
    p1 = fam1(z, Xc).fit(disp=0)
    k1, k2 = len(p1.params), part2.k
    ll = p1.llf + part2.ll
    fam.append(dict(model=nm, ll=ll, k=k1 + k2, aic=-2 * ll + 2 * (k1 + k2),
                    bic=-2 * ll + k1 * np.log(n) + k2 * np.log(rest.sum())))
fam = pd.DataFrame(fam)
fam.to_csv(TAB / "table5_model_family.csv", index=False)
R["family"] = fam.to_dict("records")

# ---------------------------------------------------------------- Table 6: coefficients (model-based SE)
t6 = mlog.table()
se_model = np.sqrt(np.clip(np.diag(mlog.V_model), 0, None))
t6["se_model"] = se_model[: len(t6)] if len(se_model) == len(t6) else np.nan
t6.to_csv(TAB / "table6_mlogit_coefficients.csv", index=False)

# ---------------------------------------------------------------- Table 7: average predicted contrasts
P0 = mlog.predict()
ame = []
for name, label, ref, levels in CAT:
    lv = sorted(levels)
    base = X.copy()
    for l in lv[1:]:
        base[f"{name}={l}"] = 0.0
    pb = mlog.predict(base)
    for l in lv[1:]:
        Xl = base.copy()
        Xl[f"{name}={l}"] = 1.0
        d = (mlog.predict(Xl) - pb).mean(0)
        for k, o in enumerate(sorted(OUT_LABELS)):
            ame.append(dict(variable=name, contrast=f"{vl[name][l]} vs {vl[name][lv[0]]}",
                            outcome=OUT_LABELS[o], estimate=d[k]))
for name, label, scale in CON:
    sd = df[name].std()
    hi, lo = X.copy(), X.copy()
    hi[name] += sd
    lo[name] -= sd
    d = (mlog.predict(hi) - mlog.predict(lo)).mean(0)
    for k, o in enumerate(sorted(OUT_LABELS)):
        ame.append(dict(variable=name, contrast=f"+1 SD versus -1 SD (SD = {sd:.3f})", outcome=OUT_LABELS[o],
                        estimate=d[k]))
pd.DataFrame(ame).to_csv(TAB / "table7_average_predicted_contrasts.csv", index=False)

with open(TAB / "model_family.json", "w") as f:
    json.dump(R, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(fam.round(4).to_string())
