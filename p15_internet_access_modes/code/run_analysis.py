"""Paper 15 analysis: ways households access the internet in Borama District.

Survey-weighted analysis of the ten predictors on the BAHDA-2026 ICT title and
variable alignment sheet: descriptives, outcome-scale scan, design-based
bivariate screening, multicollinearity, sequential multinomial models,
average marginal effects, diagnostics and sensitivity analyses.
The unweighted model family is in model_family.py.

Run:  python3 run_analysis.py      (from this folder)
"""
import json
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import log_loss, accuracy_score

from setup_data import (load, design, OUTCOME, OUT_LABELS, OUT_SHORT, CATS, CONTS, BLOCK_A, BLOCK_B,
                        BLOCK_C, PRIMARY, EXTRA, OUT)
from svy import (SvyMlogit, svy_prop, svy_mean, rao_scott, svy_anova, svychisq_f, margins, contrast,
                 level_ci, design_df)

warnings.filterwarnings("ignore")
TAB = OUT / "tables"
TAB.mkdir(parents=True, exist_ok=True)
R = {}  # key numbers for the manuscript

df, vl = load()
H, PSU, W = df["sampling_stratum"], df["psu_hh"], df["survey_weight"]
y = df[OUTCOME].astype(int)
LEVELS = [0, 1, 2, 3, 4]
CATINFO = {c[0]: c for c in CATS}
CATS = [c for c in CATS if c[0] in PRIMARY]


def lab(var, lv):
    return vl.get(var, {}).get(lv, str(lv))


# ---------------------------------------------------------------------------
# 1. Analytical sample
# ---------------------------------------------------------------------------
R["n"] = int(len(df))
R["sum_w"] = float(W.sum())
R["n_strata"] = int(H.nunique())
R["n_by_stratum"] = df.groupby("sampling_stratum").size().to_dict()
R["weights_by_stratum"] = df.groupby("sampling_stratum")["survey_weight"].first().round(3).to_dict()
R["dfd_hh"] = int(design_df(H, PSU))
R["n_urban_clusters"] = int(df.loc[df.psu_cluster.str.startswith("C_"), "psu_cluster"].nunique())
assert df["record_id"].is_unique

# ---------------------------------------------------------------------------
# 2. Outcome distribution, overall and by residence
# ---------------------------------------------------------------------------
op = svy_prop(y, W, H, PSU, LEVELS)
op["label"] = op.level.map(OUT_LABELS)
op.to_csv(TAB / "outcome_distribution_overall.csv", index=False)
R["outcome"] = op.set_index("level")[["n", "wn", "p", "lo", "hi"]].to_dict("index")
R["any_internet_p"] = float(1 - op.loc[op.level == 0, "p"].iloc[0])
z = (y != 0).astype(int)
anyp = svy_prop(z, W, H, PSU, [1])
R["any_internet"] = anyp.iloc[0][["p", "lo", "hi"]].to_dict()

byres = []
for r in [1, 2, 3]:
    s = df.residence == r
    t = svy_prop(y[s], W[s], H[s], PSU[s], LEVELS)
    t["residence"] = r
    byres.append(t)
byres = pd.concat(byres)
byres.to_csv(TAB / "outcome_by_residence.csv", index=False)
R["outcome_by_residence"] = {int(r): g.set_index("level")[["n", "p", "lo", "hi"]].to_dict("index")
                             for r, g in byres.groupby("residence")}

# ---------------------------------------------------------------------------
# 3. Table 2: sample characteristics + bivariate (weighted row %), Rao-Scott
# ---------------------------------------------------------------------------
rows = []
biv = []
for name, label, ref, levels in CATS:
    rs = svychisq_f(df[name], y, W, H, PSU)
    deff = rao_scott(df[name], y, W, H, PSU)["deff"]
    biv.append(dict(variable=name, label=label, test="Rao–Scott F", stat=rs["F"], df1=rs["df1"],
                    df2=rs["df2"], p=rs["p"], deff=deff))
    rows.append(dict(variable=name, label=label, level=None, text=label, p=rs["p"]))
    cp = svy_prop(df[name], W, H, PSU, levels)
    for _, c in cp.iterrows():
        s = df[name] == c.level
        rp = svy_prop(y[s], W[s], H[s], PSU[s], LEVELS)
        d = dict(variable=name, label=label, level=int(c.level), text=lab(name, c.level), n=int(c.n),
                 wpct=100 * c.p, wlo=100 * c.lo, whi=100 * c.hi)
        for _, q in rp.iterrows():
            d[f"row_{int(q.level)}"] = 100 * q.p
        rows.append(d)
for name, label, scale in CONTS:
    an = svy_anova(df[name], y, W, H, PSU)
    biv.append(dict(variable=name, label=label, test="Design-based Wald F", stat=an["F"], df1=an["df1"],
                    df2=an["df2"], p=an["p"], deff=np.nan))
    mm = svy_mean(df[name], W, H, PSU)
    d = dict(variable=name, label=label, level=None, text=label + ", mean (SD)", n=int(len(df)),
             umean=df[name].mean(), usd=df[name].std(), wmean=mm["mean"], wlo=mm["lo"], whi=mm["hi"],
             wsd=mm["wsd"], p=an["p"])
    for lv in LEVELS:
        s = y == lv
        d[f"row_{lv}"] = svy_mean(df.loc[s, name], W[s], H[s], PSU[s])["mean"]
    rows.append(d)
t2 = pd.DataFrame(rows)
t2.to_csv(TAB / "table2_characteristics_by_mode.csv", index=False)
biv = pd.DataFrame(biv)
biv.to_csv(TAB / "table_bivariate_screening.csv", index=False)
R["bivariate"] = biv.set_index("variable")[["stat", "df1", "df2", "p", "deff"]].to_dict("index")
R["table2"] = t2.to_dict("records")

# ---------------------------------------------------------------------------
# 4. Outcome-scale scan and sparse-cell check
# ---------------------------------------------------------------------------
scan = dict(n_categories=5, largest_share_unweighted=float(y.value_counts(normalize=True).max()),
            smallest_category_n=int(y.value_counts().min()))
R["scan"] = scan
sparse = []
for name, label, ref, levels in CATS:
    ct = pd.crosstab(df[name], y)
    for lv in ct.index:
        for c in ct.columns:
            if ct.loc[lv, c] < 5:
                sparse.append(dict(variable=name, level=int(lv), level_label=lab(name, lv), outcome=int(c),
                                   outcome_label=OUT_LABELS[c], n=int(ct.loc[lv, c])))
sparse = pd.DataFrame(sparse)
sparse.to_csv(TAB / "sparse_cells.csv", index=False)
R["sparse_cells"] = sparse.to_dict("records")

# ---------------------------------------------------------------------------
# 5. Multicollinearity: generalised VIF per predictor and VIF per indicator
# ---------------------------------------------------------------------------
Xall = design(df, PRIMARY)
Rm = np.corrcoef(Xall.to_numpy().T)
detR = np.linalg.det(Rm)
gv = []
cols = list(Xall.columns)
for name in PRIMARY:
    idx = [i for i, c in enumerate(cols) if c == name or c.startswith(name + "=")]
    oth = [i for i in range(len(cols)) if i not in idx]
    g = np.linalg.det(Rm[np.ix_(idx, idx)]) * np.linalg.det(Rm[np.ix_(oth, oth)]) / detR
    lab_ = CATINFO[name][1] if name in CATINFO else dict((c[0], c[1]) for c in CONTS)[name]
    gv.append(dict(variable=name, label=lab_, df=len(idx), gvif=g, gvif_adj=g ** (1 / (2 * len(idx)))))
gv = pd.DataFrame(gv)
gv.to_csv(TAB / "table_gvif.csv", index=False)
R["gvif_max_adj"] = float(gv.gvif_adj.max())
R["gvif"] = gv.set_index("variable")[["df", "gvif", "gvif_adj"]].to_dict("index")
A = Xall.to_numpy()
vif = []
for j, c in enumerate(cols):
    Z = np.column_stack([np.ones(len(A)), np.delete(A, j, 1)])
    e = A[:, j] - Z @ np.linalg.lstsq(Z, A[:, j], rcond=None)[0]
    vif.append(dict(variable=c.split("=")[0], term=c, vif=1 / (e @ e / ((A[:, j] - A[:, j].mean()) ** 2).sum())))
vif = pd.DataFrame(vif)
vsum = vif.groupby("variable", sort=False).vif.agg(df="size", max_vif="max", mean_vif="mean").reset_index()
vsum["tolerance"] = 1 / vsum.max_vif
vsum.to_csv(TAB / "table_vif_indicators.csv", index=False)
R["vif_max"] = float(vsum.max_vif.max())


# ---------------------------------------------------------------------------
# 6. Sequential survey-weighted multinomial models (base = No internet access)
# ---------------------------------------------------------------------------
def fit(preds, data=df, psu="psu_hh", weight="survey_weight", base=0, ridge=0.0, outcome=OUTCOME, drop=()):
    X = design(data, preds).drop(columns=list(drop))
    return SvyMlogit(data[outcome].astype(int), X, data[weight], data["sampling_stratum"], data[psu],
                     base=base, ridge=ridge).fit()


models = {
    "M1": BLOCK_A,
    "M2": BLOCK_A + BLOCK_B,
    "M3": PRIMARY,
}
fits = {k: fit(v) for k, v in models.items()}
cmp = []
for k, m in fits.items():
    i = m.info()
    cmp.append(dict(model=k, k=i["k"], ll=i["ll"], aic=i["aic"], bic=i["bic"], r2_mcf=i["r2_mcf"],
                    converged=i["converged"], n_separated=int(m.separated.sum())))
full = fits["M3"]
tab3 = full.table()
tab3.to_csv(TAB / "table3_full_model_rrr.csv", index=False)
R["full_info"] = {k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in full.info().items()}
R["separated_terms"] = tab3.loc[tab3.separated, ["outcome", "term"]].to_dict("records")

# joint Wald tests per predictor in the full model
jw = []
for name in PRIMARY:
    cs = [c for c in full.names if c == name or c.startswith(name + "=")]
    t = full.wald(cs)
    jw.append(dict(variable=name, F=t["F"], df1=t["df1"], df2=t["df2"], p=t["p"]))
jw = pd.DataFrame(jw)
jw.to_csv(TAB / "table3_joint_wald.csv", index=False)
R["joint_wald"] = jw.set_index("variable").to_dict("index")

# crude (single-predictor) RRRs
crude = []
for name in PRIMARY:
    m = fit([name])
    t = m.table()
    t = t[t.term != "_cons"]
    t["variable"] = name
    crude.append(t)
crude = pd.concat(crude)
crude.to_csv(TAB / "table_crude_rrr.csv", index=False)

# classification check
P = full.predict()
pred = np.array(LEVELS)[P.argmax(1)]
wn = W / W.sum()
cm = pd.crosstab(pd.Series(y.values, name="observed"), pd.Series(pred, name="predicted"))
cm.to_csv(TAB / "classification_unweighted.csv")
R["accuracy_unweighted"] = float((pred == y.values).mean())
R["accuracy_weighted"] = float((wn * (pred == y.values)).sum())
R["null_accuracy_weighted"] = float(max((wn * (y.values == l)).sum() for l in LEVELS))
# calibration: weighted mean predicted vs observed by outcome
R["calibration"] = {int(l): dict(obs=float((wn * (y.values == l)).sum()), pred=float((wn * P[:, i]).sum()))
                    for i, l in enumerate(LEVELS)}

# ---------------------------------------------------------------------------
# 7. Average adjusted predictions and AMEs
# ---------------------------------------------------------------------------
def setter(var, lv, levels, ref):
    def f(X):
        for l in levels:
            if l == ref:
                continue
            X[f"{var}={l}"] = 1.0 if l == lv else 0.0
        return X
    return f


ame_rows = []
pp_rows = []
for name, label, ref, levels in CATS:
    labs = [str(l) for l in levels]
    mr = margins(full, [setter(name, l, levels, ref) for l in levels], labs)
    for l in levels:
        pc = level_ci(full, mr, str(l))
        for _, r in pc.iterrows():
            pp_rows.append(dict(variable=name, level=l, level_label=lab(name, l), outcome=int(r.level),
                                pr=r.pr, lo=r.lo, hi=r.hi))
        if l == ref:
            continue
        c = contrast(full, mr, str(l), str(ref))
        for _, r in c.iterrows():
            ame_rows.append(dict(variable=name, label=label, level=l, level_label=lab(name, l), ref=ref,
                                 ref_label=lab(name, ref), outcome=int(r.level), ame=r.ame, lo=r.lo, hi=r.hi,
                                 p=r.p))
# continuous: +10 years of age, +1 household member (finite-difference AME)
for name, label, scale in CONTS:
    def plus(X, name=name):
        X[name] = X[name] + 1.0
        return X
    mr = margins(full, [lambda X: X, plus], ["base", "plus"])
    c = contrast(full, mr, "plus", "base")
    unit = "+10 years" if name == "head_age" else "+1 member"
    for _, r in c.iterrows():
        ame_rows.append(dict(variable=name, label=label, level=unit, level_label=unit, ref=None, ref_label="",
                             outcome=int(r.level), ame=r.ame, lo=r.lo, hi=r.hi, p=r.p))
ame = pd.DataFrame(ame_rows)
ame.to_csv(TAB / "table4_ame.csv", index=False)
pp = pd.DataFrame(pp_rows)
pp.to_csv(TAB / "adjusted_predictions.csv", index=False)
R["ame"] = ame.to_dict("records")
R["pp"] = pp.to_dict("records")

# ---------------------------------------------------------------------------
# 8. Diagnostics: functional form, IIA, influence
# ---------------------------------------------------------------------------
# (a) Linearity in the logit for age and household size: add squared terms
d2 = df.copy()
Xq = design(d2, PRIMARY)
Xq["head_age_sq"] = (d2.head_age / 10) ** 2
Xq["household_size_sq"] = d2.household_size ** 2
mq = SvyMlogit(y, Xq, W, H, PSU).fit()
R["nonlinearity"] = {
    "age": mq.wald(["head_age_sq"]),
    "hhsize": mq.wald(["household_size_sq"]),
}

# (b) Hausman–McFadden IIA test (unweighted model-based, as in Stata's mlogtest/hausman)
Xf = design(df, PRIMARY)
mu = SvyMlogit(y, Xf, np.ones(len(df)), H, PSU).fit()
iia = []
k = mu.X.shape[1]
for drop in [1, 2, 3, 4]:
    keep = df[OUTCOME] != drop
    Xr = Xf[keep]
    Xr = Xr.loc[:, Xr.std() > 0]
    mr_ = SvyMlogit(y[keep], Xr, np.ones(keep.sum()), H[keep], PSU[keep]).fit()
    # compare common coefficients (all remaining non-base equations, common columns, excluding constants)
    comm_cols = [c for c in Xr.columns]
    bi, bf = [], []
    for a in mr_.alts:
        for c in comm_cols:
            j_r = mr_.alts.index(a) * mr_.X.shape[1] + mr_.names.index(c)
            j_f = mu.alts.index(a) * k + mu.names.index(c)
            if mr_.separated[j_r] or mu.separated[j_f]:
                continue
            bi.append(j_r)
            bf.append(j_f)
    d = mr_.beta[bi] - mu.beta[bf]
    Vd = mr_.V_model[np.ix_(bi, bi)] - mu.V_model[np.ix_(bf, bf)]
    stat = float(d @ np.linalg.pinv(Vd) @ d)
    ev = np.linalg.eigvalsh(Vd)
    dfh = int(np.linalg.matrix_rank(Vd))
    iia.append(dict(omitted=OUT_LABELS[drop], chi2=stat, df=dfh, p=float(stats.chi2.sf(max(stat, 0), dfh)),
                    vd_not_pd=bool((ev < 0).any())))
iia = pd.DataFrame(iia)
iia.to_csv(TAB / "diag_iia_hausman.csv", index=False)
R["iia"] = iia.to_dict("records")

# (c) Influence: refit without the 1% of households with the largest weighted score norm
infl = np.sqrt((full.scores ** 2).sum(1))
cut = np.quantile(infl, 0.99)
sub = df[infl < cut]
R["influence_dropped"] = int((infl >= cut).sum())

# ---------------------------------------------------------------------------
# 9. Sensitivity analyses (Supplementary Table S2)
# ---------------------------------------------------------------------------
KEY = [("residence=2", 3), ("residence=3", 3), ("residence=3", 1), ("smartphone=1", 1),
       ("monthly_expenditure=5", 3), ("electricity_source=4", 1), ("electricity_source=4", 3),
       ("head_education=4", 3), ("head_employment=4", 3), ("youth_vocational_training=1", 3)]


def keyrows(m, tag):
    t = m.table()
    out = []
    for term, o in KEY:
        r = t[(t.term == term) & (t.outcome == o)]
        if len(r):
            r = r.iloc[0]
            out.append(dict(analysis=tag, term=term, outcome=o, rrr=r.rrr, lo=r.lo, hi=r.hi, p=r.p,
                            separated=r.separated))
    return out


sens = []
sens += keyrows(full, "S0 Primary: survey-weighted, strata, household PSU")
sens += keyrows(fit(PRIMARY, psu="psu_cluster"), "S1 Urban sub-zone clusters as PSU")
df["_one"] = 1.0
sens += keyrows(fit(PRIMARY, weight="_one"), "S2 Unweighted")
# with "None" set to missing the no-schooling reference is empty, so primary education becomes the reference
sens += keyrows(fit(PRIMARY, data=df[df.head_education != 0].copy(), drop=["head_education=1"]),
                "S3 Education 'none' treated as missing")
sens += keyrows(fit(BLOCK_A + BLOCK_B), "S4 Smartphone ownership removed (M2)")
s5 = fit(PRIMARY + EXTRA)
sens += keyrows(s5, "S5 Five further household ICT items added")
R["s5_info"] = {k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in s5.info().items()}
sens += keyrows(fit(PRIMARY, data=sub.copy()), "S6 Top 1% influential households removed")
d4 = df.copy()
d4["y4"] = d4[OUTCOME].replace({4: 3})
sens += keyrows(fit(PRIMARY, data=d4, outcome="y4"), "S7 Public Wi-Fi merged with Home Wi-Fi (4 categories)")
sens += keyrows(fit(PRIMARY, ridge=1.0), "S8 Ridge-penalised (lambda = 1)")
sens = pd.DataFrame(sens)
sens.to_csv(TAB / "tableS2_sensitivity.csv", index=False)
R["sensitivity"] = sens.to_dict("records")
R["n_edu_none"] = int((df.head_education == 0).sum())

# alternative baseline: smartphone data as base
alt = fit(PRIMARY, base=1)
alt.table().to_csv(TAB / "tableS3_alt_baseline_smartphone.csv", index=False)

# ---------------------------------------------------------------------------
# 10. Survey-weighted penalised multinomial models (cross-validated)
# ---------------------------------------------------------------------------
Xs = design(df, PRIMARY).to_numpy()
mu_, sd_ = Xs.mean(0), Xs.std(0)
Xz = (Xs - mu_) / sd_
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=2026)
specs = {
    "Multinomial logit (unpenalised)": dict(penalty=None, solver="lbfgs"),
    "Ridge multinomial": dict(penalty="l2", C=0.1, solver="lbfgs"),
    "Lasso multinomial": dict(penalty="l1", C=0.1, solver="saga"),
    "Elastic-net multinomial": dict(penalty="elasticnet", C=0.1, l1_ratio=0.5, solver="saga"),
}
mc = []
for nm, sp in specs.items():
    ll, acc = [], []
    for tr, te in skf.split(Xz, y):
        clf = LogisticRegression(max_iter=5000, **sp)
        clf.fit(Xz[tr], y.values[tr], sample_weight=W.values[tr])
        pr = clf.predict_proba(Xz[te])
        ll.append(log_loss(y.values[te], pr, sample_weight=W.values[te], labels=LEVELS))
        acc.append(accuracy_score(y.values[te], pr.argmax(1), sample_weight=W.values[te]))
    clf = LogisticRegression(max_iter=5000, **sp).fit(Xz, y.values, sample_weight=W.values)
    nz = int((np.abs(clf.coef_) > 1e-6).sum())
    mc.append(dict(model=nm, cv_logloss=np.mean(ll), cv_accuracy=np.mean(acc), nonzero_coef=nz))
mc = pd.DataFrame(mc)
cmp = pd.DataFrame(cmp)
cmp.to_csv(TAB / "table5_model_comparison_sequential.csv", index=False)
mc.to_csv(TAB / "table5_model_comparison_penalised.csv", index=False)
R["model_cmp"] = cmp.to_dict("records")
R["model_cmp_pen"] = mc.to_dict("records")
R["dfd"] = int(full.dfd)

with open(OUT / "results.json", "w") as f:
    json.dump(R, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print("done", R["n"], R["full_info"])
