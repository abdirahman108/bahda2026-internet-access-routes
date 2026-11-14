"""Step 5: Draw Figures 1 to 3 and Supplementary Figure S1.

Run this script after 2_run_analysis.py and 3_model_family.py, because it reads their results.
From the repository's main folder, run:

    python3 scripts/5_make_figures.py

The figures are saved in outputs/figures/.
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd

import _paths  # noqa: F401  (puts lib/ on the import path)
from variables import OUT, OUT_SHORT

FIG = OUT / "figures"
FIG.mkdir(parents=True, exist_ok=True)
TAB = OUT / "tables"
R = json.load(open(OUT / "results.json"))

plt.rcParams.update({"font.family": "DejaVu Serif", "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#52514e", "axes.labelcolor": "#0b0b0b",
                     "xtick.color": "#52514e", "ytick.color": "#52514e", "savefig.dpi": 300})
# One colour per route, always in the same order (outcome codes 0 to 4)
COL = {0: "#2a78d6", 1: "#eb6834", 2: "#1baf7a", 3: "#eda100", 4: "#e87ba4"}
# A pattern per route as well, so the bars can be told apart without colour
HATCH = {0: "", 1: "///", 2: "...", 3: "xx", 4: "---"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e0"
LEV = [0, 1, 2, 3, 4]


# ---------------------------------------------------------------- Figure 1
def box(ax, x, y, w, h, text, bold=False):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.01,rounding_size=0.015",
                                fc="white", ec=INK, lw=0.8))
    ax.text(x, y, text, ha="center", va="center", fontsize=8.5, weight="bold" if bold else "normal", wrap=True)


fig, ax = plt.subplots(figsize=(6.3, 5.0))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
box(ax, 0.38, 0.93, 0.72, 0.09, "BAHDA-2026 Survey: submissions received\nN = 2,923 (6 strata, 24 zones, 96 clusters)")
box(ax, 0.80, 0.81, 0.38, 0.08, "Excluded: n = 27\nNo consent recorded")
box(ax, 0.38, 0.69, 0.72, 0.12, "Consented household interviews, all with a valid response\non the outcome (main internet access route)\nN = 2,896")
box(ax, 0.80, 0.52, 0.38, 0.15, "Excluded: n = 189\nMonthly expenditure reported\nas “Prefer not to say”\n(no other missing predictor)")
box(ax, 0.38, 0.30, 0.62, 0.10, "Complete cases on the outcome, 10 predictors,\nweight and stratum\nn = 2,707", bold=True)
box(ax, 0.38, 0.09, 0.70, 0.12,
    "Final unweighted analytical sample: n = 2,707\nUrban 2,295 | Peri-urban 201 | Rural 211\nSum of normalised weights = 2,705.4 (not a sample size)")
for y0, y1 in [(0.885, 0.75), (0.63, 0.35), (0.25, 0.15)]:
    ax.annotate("", xy=(0.38, y1), xytext=(0.38, y0), arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.8))
for yy_ in (0.52, 0.81):
    ax.annotate("", xy=(0.61, yy_), xytext=(0.38, yy_), arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.8))
fig.savefig(FIG / "Figure1_sample_flow.png", bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------- Figure 2
res = pd.read_csv(TAB / "outcome_by_residence.csv")
ov = pd.read_csv(TAB / "outcome_distribution_overall.csv")
ov["residence"] = 0
d = pd.concat([ov[["level", "p", "lo", "hi", "residence"]], res[["level", "p", "lo", "hi", "residence"]]])
groups = {0: "Borama District\n(all households)", 1: "Urban", 2: "Peri-urban", 3: "Rural"}
fig, ax = plt.subplots(figsize=(6.5, 3.9))
bw = 0.15
x = np.arange(4)
for i, lv in enumerate(LEV):
    s = d[d.level == lv].set_index("residence").loc[[0, 1, 2, 3]]
    xs = x + (i - 2) * (bw + 0.012)
    ax.bar(xs, 100 * s.p, width=bw, color=COL[lv], label=OUT_SHORT[lv], zorder=2, hatch=HATCH[lv],
           edgecolor="white", linewidth=0.3)
    for xv, pv, hv in zip(xs, 100 * s.p, 100 * s.hi):
        ax.text(xv, hv + 0.8, f"{pv:.0f}", ha="center", va="bottom", fontsize=5.8, color=INK)
    ax.errorbar(xs, 100 * s.p, yerr=[100 * (s.p - s.lo), 100 * (s.hi - s.p)], fmt="none", ecolor=MUTED,
                elinewidth=0.7, capsize=1.5, zorder=3)
ax.set_xticks(x)
ax.set_xticklabels([groups[g] for g in [0, 1, 2, 3]])
ax.set_ylabel("Weighted percentage of households (%)")
ax.yaxis.grid(True, color=GRID, lw=0.6, zorder=0)
ax.set_axisbelow(True)
ax.legend(ncol=5, fontsize=7.2, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.12))
fig.savefig(FIG / "Figure2_outcome_by_residence.png", bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------- Figure 3
pp = pd.read_csv(TAB / "adjusted_predictions.csv")
panels = [("residence", "A. Residence", ["Urban", "Peri-urban", "Rural"]),
          ("monthly_expenditure", "B. Monthly expenditure (US$)", ["<100", "100–299", "300–599", "600–999", "≥1,000"]),
          ("electricity_source", "C. Electricity source", ["Grid", "Solar", "Generator", "None"]),
          ("smartphone", "D. Household owns a smartphone", ["No", "Yes"])]
fig, axes = plt.subplots(2, 2, figsize=(7.0, 4.3), sharey=True)
for ax, (var, title, ticks) in zip(axes.ravel(), panels):
    s = pp[pp.variable == var]
    lvls = sorted(s.level.unique())
    xs = np.arange(len(lvls))
    for j, lv in enumerate(LEV):
        q = s[s.outcome == lv].set_index("level").loc[lvls]
        off = (j - 2) * 0.07
        # Join the points with lines only for spending, whose categories have a natural order
        ax.plot(xs + off, 100 * q.pr, color=COL[lv], lw=1.6 if var == "monthly_expenditure" else 0,
                marker="o", ms=4, label=OUT_SHORT[lv], zorder=3)
        ax.vlines(xs + off, 100 * q.lo.clip(lower=0), 100 * q.hi, color=COL[lv], lw=0.8, alpha=0.8, zorder=2)
    ax.set_xticks(xs)
    ax.set_xticklabels(ticks, fontsize=7.8)
    ax.set_title(title, loc="left", fontsize=9.5, color=INK)
    ax.yaxis.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
fig.supylabel("Adjusted predicted probability (%)", fontsize=9)
h, l = axes[0, 0].get_legend_handles_labels()
fig.legend(h, l, ncol=5, frameon=False, fontsize=7.6, loc="upper center", bbox_to_anchor=(0.5, 1.02))
fig.tight_layout(rect=(0, 0, 1, 0.96))
fig.savefig(FIG / "Figure3_adjusted_predictions.png", bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------- Supplementary Figure S1
ame = pd.read_csv(TAB / "table4_ame.csv")
sel = [("residence", "2", "Peri-urban vs urban"), ("residence", "3", "Rural vs urban"),
       ("monthly_expenditure", "3", "US$300–599 vs <US$100"), ("monthly_expenditure", "5", "≥US$1,000 vs <US$100"),
       ("electricity_source", "2", "Solar vs grid"), ("electricity_source", "4", "No electricity vs grid"),
       ("smartphone", "1", "Owns smartphone"), ("head_education", "4", "University vs primary"),
       ("head_employment", "2", "Private vs self-employed"), ("head_employment", "4", "Government vs self-employed"),
       ("youth_vocational_training", "1", "Youth vocational training")]
fig, axes = plt.subplots(1, 4, figsize=(7.2, 4.6), sharey=True)
outs = [0, 1, 2, 3]
ylab = [s[2] for s in sel]
yy = np.arange(len(sel))[::-1]
for ax, o in zip(axes, outs):
    for k, (v, lv, _) in enumerate(sel):
        r = ame[(ame.variable == v) & (ame.level.astype(str) == lv) & (ame.outcome == o)].iloc[0]
        ax.hlines(yy[k], 100 * r.lo, 100 * r.hi, color=COL[o], lw=1.2)
        ax.plot(100 * r.ame, yy[k], "o", color=COL[o], ms=4.5, mec="white", mew=0.6)
    ax.axvline(0, color=MUTED, lw=0.7, ls="--")
    ax.set_title(OUT_SHORT[o], fontsize=8.5, color=INK)
    ax.xaxis.grid(True, color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", labelsize=7.5)
axes[0].set_yticks(yy)
axes[0].set_yticklabels(ylab, fontsize=7.8)
fig.supxlabel("Average marginal effect (percentage points, 95% CI)", fontsize=8.5)
fig.tight_layout()
fig.savefig(FIG / "FigureS1_average_marginal_effects.png", bbox_inches="tight")
plt.close(fig)
print("figures written")
