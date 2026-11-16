"""Step 2: Run the main analysis of how households in Borama District access the internet.

This script uses the survey weights throughout. It does the following, in order:

1. Describes the 2,707 households and how many use each route to the internet.
2. Builds Table 2 and tests how each predictor relates to the route.
3. Checks that no two predictors measure the same thing.
4. Fits three models, each adding a group of predictors (Table 3).
5. Converts the main model into percentage-point differences and predicted percentages (Table 4,
   Figure 3).
6. Runs model checks and the sensitivity analyses S1 to S15 (Supplementary Table S2).

To run this script, from the repository's main folder, run:

    python3 scripts/2_run_analysis.py

The results are saved in the outputs/ folder.
"""
import json
import warnings

import numpy as np
import pandas as pd
from scipy import stats

import _paths  # noqa: F401  (puts lib/ on the import path)
from variables import (load, design, OUTCOME, OUT_LABELS, CATS, CONTS, BLOCK_A, BLOCK_B,
                        BLOCK_C, PRIMARY, EXTRA, OUT)
from atlas_margins import calibrated_weights
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
# 1. The 2,707 households in the analysis
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
# 2. How many households use each route, overall and by area
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
# 3. Table 2: household characteristics by route (weighted row %), with Rao-Scott tests
# ---------------------------------------------------------------------------
rows = []
rowci = []  # unweighted cell counts and 95% CIs for every row percentage in Table 2
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
            rowci.append(dict(variable=name, label=label, level=int(c.level), level_label=lab(name, c.level),
                              n_row=int(c.n), outcome=int(q.level), outcome_label=OUT_LABELS[int(q.level)],
                              n_cell=int(q.n), pct=100 * q.p, lo=100 * q.lo, hi=100 * q.hi))
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
pd.DataFrame(rowci).to_csv(TAB / "tableS_table2_row_ci.csv", index=False)
biv = pd.DataFrame(biv)
biv.to_csv(TAB / "table_bivariate_screening.csv", index=False)
R["bivariate"] = biv.set_index("variable")[["stat", "df1", "df2", "p", "deff"]].to_dict("index")
R["table2"] = t2.to_dict("records")

# ---------------------------------------------------------------------------
# 4. Check the outcome categories and find combinations with very few households
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
# 5. Check that no two predictors overlap too much (variance inflation factors)
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
# 6. Fit Models 1 to 3, each adding predictors; every route is compared with no internet access
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

# Test each predictor as a whole in the main model
jw = []
for name in PRIMARY:
    cs = [c for c in full.names if c == name or c.startswith(name + "=")]
    t = full.wald(cs)
    jw.append(dict(variable=name, F=t["F"], df1=t["df1"], df2=t["df2"], p=t["p"]))
jw = pd.DataFrame(jw)
jw.to_csv(TAB / "table3_joint_wald.csv", index=False)
R["joint_wald"] = jw.set_index("variable").to_dict("index")

# Test each added group of predictors as a whole (design-adjusted Wald test), in the model that adds it
def block_cols(m, block):
    return [c for c in m.names if any(c == v or c.startswith(v + "=") for v in block)]


bw = []
for mk, block, what in [("M2", BLOCK_B, "Resources and infrastructure block added to Model 1"),
                        ("M3", BLOCK_C, "Smartphone ownership added to Model 2")]:
    t = fits[mk].wald(block_cols(fits[mk], block))
    bw.append(dict(model=mk, block=what, F=t["F"], df1=t["df1"], df2=t["df2"], p=t["p"]))
bw = pd.DataFrame(bw)
bw.to_csv(TAB / "table_block_wald.csv", index=False)
R["block_wald"] = bw.to_dict("records")

# How much clustering each result can absorb: the factor by which a standard error could grow before
# the 95% CI of the relative risk ratio includes 1, and the matching design effect (the factor squared)
cmg = tab3[(tab3.term != "_cons") & (~tab3.separated)].copy()
crit = (np.log(cmg.hi) - cmg.b) / cmg.se
cmg["se_inflation_tolerated"] = cmg.b.abs() / (crit * cmg.se)
cmg["deff_tolerated"] = cmg.se_inflation_tolerated ** 2
cmg = cmg[cmg.se_inflation_tolerated > 1]
cmg[["outcome", "term", "rrr", "lo", "hi", "se_inflation_tolerated", "deff_tolerated"]].to_csv(
    TAB / "table_clustering_margin.csv", index=False)

# Relative risk ratios for each predictor on its own (Supplementary Table S3)
crude = []
for name in PRIMARY:
    m = fit([name])
    t = m.table()
    t = t[t.term != "_cons"]
    t["variable"] = name
    crude.append(t)
crude = pd.concat(crude)
crude.to_csv(TAB / "table_crude_rrr.csv", index=False)

# Compare each household's predicted route with its actual route
P = full.predict()
pred = np.array(LEVELS)[P.argmax(1)]
wn = W / W.sum()
cm = pd.crosstab(pd.Series(y.values, name="observed"), pd.Series(pred, name="predicted"))
cm.to_csv(TAB / "classification_unweighted.csv")
R["accuracy_unweighted"] = float((pred == y.values).mean())
R["accuracy_weighted"] = float((wn * (pred == y.values)).sum())
R["null_accuracy_weighted"] = float(max((wn * (y.values == l)).sum() for l in LEVELS))
# Compare the average predicted share of each route with the actual share
R["calibration"] = {int(l): dict(obs=float((wn * (y.values == l)).sum()), pred=float((wn * P[:, i]).sum()))
                    for i, l in enumerate(LEVELS)}

# ---------------------------------------------------------------------------
# 7. Predicted percentages and percentage-point differences (AMEs)
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
# For age and household size, compare +10 years of age and +1 household member
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
# 8. Model checks: straight-line effects, IIA, and influential households
# ---------------------------------------------------------------------------
# (a) Check that age and household size have straight-line effects by adding squared terms
Xq = Xall.copy()
Xq["head_age_sq"] = (df.head_age / 10) ** 2
Xq["household_size_sq"] = df.household_size ** 2
mq = SvyMlogit(y, Xq, W, H, PSU).fit()
R["nonlinearity"] = {
    "age": mq.wald(["head_age_sq"]),
    "hhsize": mq.wald(["household_size_sq"]),
}

# (b) Hausman–McFadden IIA test (unweighted model-based, as in Stata's mlogtest/hausman)
Xf = Xall
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

# (c) Refit the model without the 1% of households that influence the results most
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


def keyrows(m, tag, extra=()):
    t = m.table()
    out = []
    for term, o in list(KEY) + list(extra):
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
# S3: leave out the households whose education was not reported
sens += keyrows(fit(PRIMARY, data=df[df.head_education != 0].copy(), drop=["head_education=0"]),
                "S3 Education not reported: households dropped")
sens += keyrows(fit(BLOCK_A + BLOCK_B), "S4 Smartphone ownership removed (M2)")
s5 = fit(PRIMARY + EXTRA)
sens += keyrows(s5, "S5 Five further household ICT items added")
R["s5_info"] = {k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in s5.info().items()}
# The 15-predictor model joins the AIC/BIC comparison as Model 4 (same 2,707 households)
i = s5.info()
cmp.append(dict(model="M4", k=i["k"], ll=i["ll"], aic=i["aic"], bic=i["bic"], r2_mcf=i["r2_mcf"],
                converged=i["converged"], n_separated=int(s5.separated.sum())))
sens += keyrows(fit(PRIMARY, data=sub.copy()), "S6 Top 1% influential households removed")
d4 = df.copy()
d4["y4"] = d4[OUTCOME].replace({4: 3})
sens += keyrows(fit(PRIMARY, data=d4, outcome="y4"), "S7 Public Wi-Fi merged with Home Wi-Fi (4 categories)")
sens += keyrows(fit(PRIMARY, ridge=1.0), "S8 Ridge-penalised (lambda = 1)")
# S9 and S10: change the set of routes, to check the IIA assumption where it is most likely to fail
d9 = df[df[OUTCOME] != 4].copy()
sens += keyrows(fit(PRIMARY, data=d9), "S9 Public Wi-Fi/cyber café category dropped")
d10 = df.copy()
d10["y10"] = d10[OUTCOME].replace({2: 1})
sens += keyrows(fit(PRIMARY, data=d10, outcome="y10"), "S10 Smartphone and feature-phone data merged")
# S11: cap the peri-urban weight at 3, then rescale all weights to add up to the sample size
d11 = df.copy()
d11["w_trim"] = d11.survey_weight.clip(upper=3.0)
d11["w_trim"] *= len(d11) / d11.w_trim.sum()
sens += keyrows(fit(PRIMARY, data=d11, weight="w_trim"), "S11 Weights capped at 3 and renormalised")
# S12: adjust the weights to match the Atlas totals for all 2,896 households (stratum, route,
# employment, and electricity), to stand in for the 189 households left out
d12 = df.copy()
d12["w_cal"] = calibrated_weights(d12)
sens += keyrows(fit(PRIMARY, data=d12, weight="w_cal"), "S12 Weights calibrated to full-sample margins")
R["calibrated_weight_range"] = [float(d12.w_cal.min()), float(d12.w_cal.max())]
# S13: the same model with the "Missing/unspecified" education group (raw label "None") as the comparison
# group instead of primary education. Only the education rows change; the fit is identical.
X13 = design(df, PRIMARY).drop(columns=["head_education=0"])
X13.insert(0, "head_education=1", (df.head_education == 1).astype(float))
s13 = SvyMlogit(y, X13, W, H, PSU).fit()
t13 = s13.table()
t13[t13.term.str.startswith("head_education")].to_csv(TAB / "tableS_education_alt_reference.csv", index=False)
R["s13_ll"] = float(s13.info()["ll"])
sens += keyrows(s13, "S13 Education: Missing/unspecified group as reference")
# S14: household size in four groups instead of a straight line
d14 = df.copy()
X14 = design(d14, PRIMARY).drop(columns=["household_size"])
hs = pd.cut(d14.household_size, [0, 5, 8, 11, np.inf], labels=["1-5", "6-8", "9-11", "12+"])
R["s14_household_size_groups"] = hs.value_counts().sort_index().to_dict()
for g in ["1-5", "9-11", "12+"]:  # comparison group: 6 to 8 members
    X14[f"household_size_group={g}"] = (hs == g).astype(float).to_numpy()
s14 = SvyMlogit(y, X14, W, H, PSU).fit()
R["s14_household_size_wald"] = s14.wald([c for c in s14.names if c.startswith("household_size_group")])
t14 = s14.table()
t14[t14.term.str.startswith("household_size_group")].to_csv(TAB / "tableS_household_size_groups.csv",
                                                             index=False)
sens += keyrows(s14, "S14 Household size in four groups")
# S15: the two highest spending bands (US$600-999 and US$1,000 or more) merged into one
d15 = df.copy()
d15["monthly_expenditure"] = d15.monthly_expenditure.replace({5: 4})
X15 = design(d15, PRIMARY).drop(columns=["monthly_expenditure=5"])
s15 = SvyMlogit(y, X15, W, H, PSU).fit()
sens += keyrows(s15, "S15 Top two expenditure bands merged (US$600 or more)",
                extra=[("monthly_expenditure=4", 3), ("monthly_expenditure=4", 1)])
sens = pd.DataFrame(sens)
sens.to_csv(TAB / "tableS2_sensitivity.csv", index=False)
R["sensitivity"] = sens.to_dict("records")
R["n_edu_none"] = int((df.head_education == 0).sum())

# Effective sample size: how many equally weighted households the weighted sample is worth
R["kish_deff"] = float(len(W) * (W ** 2).sum() / W.sum() ** 2)
R["kish_neff"] = float(W.sum() ** 2 / (W ** 2).sum())
R["weight_share_by_stratum"] = (df.groupby("sampling_stratum").survey_weight.sum() / W.sum()).round(4).to_dict()
# Households per estimated parameter for each route in the main model
kpar = full.X.shape[1]
R["events_per_parameter"] = {int(l): dict(n=int((y == l).sum()), k=int(kpar), epp=float((y == l).sum() / kpar))
                             for l in LEVELS[1:]}
# Routes used by households without a smartphone (they may share a device)
R["no_smartphone_outcome"] = y[df.smartphone == 0].value_counts().sort_index().to_dict()
# Model 2: all relative risk ratios without smartphone ownership
fits["M2"].table().to_csv(TAB / "table_model2_rrr.csv", index=False)

# Supplementary Table S4: compare every route with smartphone data instead
alt = fit(PRIMARY, base=1)
alt.table().to_csv(TAB / "tableS3_alt_baseline_smartphone.csv", index=False)

# ---------------------------------------------------------------------------
# 10. Compare Models 1 to 4 on AIC and BIC
# ---------------------------------------------------------------------------
cmp = pd.DataFrame(cmp)
cmp.to_csv(TAB / "table5_model_comparison_sequential.csv", index=False)
# AIC and BIC side by side: difference from the best model on each criterion and which model each favours
ic = cmp[["model", "k", "ll", "aic", "bic"]].copy()
ic["delta_aic"] = ic.aic - ic.aic.min()
ic["delta_bic"] = ic.bic - ic.bic.min()
ic.to_csv(TAB / "table5_information_criteria.csv", index=False)
R["ic_best"] = {"aic": ic.loc[ic.aic.idxmin(), "model"], "bic": ic.loc[ic.bic.idxmin(), "model"]}
R["model_cmp"] = cmp.to_dict("records")
R["dfd"] = int(full.dfd)

with open(OUT / "results.json", "w") as f:
    json.dump(R, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print("done", R["n"], R["full_info"])
