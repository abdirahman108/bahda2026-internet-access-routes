# Paper 15: Ways households access the internet in Borama District (BAHDA-2026)

Analysis code for the BAHDA-2026 Paper 15 manuscript. Predictors are the ten variables of the
BAHDA-2026 ICT title and variable alignment sheet (IV1–IV10); the outcome is the household's main way of
accessing the internet at home (five nominal categories).

| Step | File | What it does |
|---|---|---|
| 1 | `code/01_clean_p15.do` | Stata cleaning script: keeps the outcome, predictors and design fields, recodes, drops incomplete cases, asserts N = 2,707 |
| 2 | `code/run_analysis.py` | Survey-weighted descriptives, Rao–Scott tests, VIF/GVIF, sequential multinomial logit models (weights + strata, linearised variance), AMEs, diagnostics, sensitivity analyses, penalised models |
| 3 | `code/model_family.py` | Unweighted model family: multinomial logit, ridge/lasso/elastic-net (CV deviance), alternative baseline, two-part nominal logit and probit; unweighted screening, VIF, coefficients and predicted contrasts |
| 4 | `code/make_figures.py` | Figures 1–4 |
| – | `code/02_analysis_p15.do` | Stata equivalent of steps 2–3 |
| – | `code/svy.py` | Design-based estimators (Taylor linearisation, Rao–Scott second-order F, survey multinomial logit, margins) |
| – | `code/setup_data.py` | Variable definitions, reference categories and model blocks |
| 5 | `code/verify_outputs.py` | Checks 23 key results of a fresh run against the manuscript |

Outputs are written to `output/tables`, `output/figures` and `output/results.json` (not tracked).

## Running

**See [REPRODUCE.md](REPRODUCE.md) for the full step-by-step reproduction guide**, including data access,
environment setup, and a map from every manuscript table and figure to its output file.

```
pip install -r requirements.txt
cd p15_internet_access_modes/code
bash run_all.sh        # runs the analysis, model family and figures, then verify_outputs.py
```

The scripts expect the cleaned extract at `data/p15_internet_access_modes_clean.dta`.
**The microdata are not in this repository**: BAHDA-2026 household records are held by Amoud University under its
data-governance procedures.

## Design notes

- Weight `survey_weight` (source `wgt`, normalised model-assisted stratum weight), strata `sampling_stratum` (6).
- Households are treated as PSUs because complete cluster codes are unavailable for the peri-urban and rural strata;
  sensitivity S1 uses the 64 urban sub-zone clusters.
- Results correspond to Stata `svyset record_id [pw=survey_weight], strata(sampling_stratum)` followed by
  `svy: mlogit ..., baseoutcome(0) rrr`, and to R `survey::svychisq(..., statistic = "F")` for the bivariate tests.
- The education option "None" is coded as no schooling (as in the cleaning script); sensitivity S3 treats it as missing.
