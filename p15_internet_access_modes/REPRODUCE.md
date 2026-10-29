# Reproducing the Paper 15 results

This guide explains how to reproduce every table and figure in the manuscript *Ways Households Access the
Internet in Borama District, Somaliland: Evidence from the BAHDA-2026 Household Survey* from the BAHDA-2026
microdata. A full run takes about five minutes on a laptop. The last step checks 23 key numbers from the
manuscript automatically.

## 1. What you need

| Item | Notes |
|---|---|
| BAHDA-2026 microdata | Not in this repository (see step 2). |
| Python 3.11 or newer | Results were produced with Python 3.13 and the package versions in `requirements.txt`. |
| Stata 16 or newer (optional) | Needed only to rebuild the analytical file from the raw survey file, or to run the Stata version of the analysis. |
| Repository access | The repository is private. Request access from the corresponding author (abdirahman@amoud.edu.so) with your GitHub username. |
| git | To clone the repository. |

The repository layout:

```
p15_internet_access_modes/
├── REPRODUCE.md            this guide
├── requirements.txt        pinned Python packages
├── data/                   place the .dta file here (ignored by git)
├── output/                 created by the scripts (ignored by git)
└── code/
    ├── 01_clean_p15.do     raw BAHDA-2026 file -> analytical file (Stata)
    ├── 02_analysis_p15.do  Stata version of the analysis
    ├── setup_data.py       variable definitions, reference categories, model blocks
    ├── svy.py              design-based estimators (survey weights, strata, linearised variance)
    ├── run_analysis.py     survey-weighted analysis (Tables 2-4, S1-S4, S6; Figures 2-4)
    ├── model_family.py     unweighted model family (Table S5)
    ├── make_figures.py     Figures 1-4
    ├── verify_outputs.py   compares a fresh run with the manuscript
    └── run_all.sh          runs everything in order
```

## 2. Get the data

The BAHDA-2026 household microdata are held by Amoud University and are not redistributed, because they
contain confidential household records. Reviewers and other researchers can request access through the
Amoud University Research and Innovation Center under its data-governance procedures. Never commit a
`.dta` file to the repository: `.gitignore` excludes `*.dta` and every `data/` folder.

You will receive one of two files:

- **The Paper 15 analytical file** (2,707 households, 21 variables, including `DV_internet_access_mode`).
  Save it as `p15_internet_access_modes/data/p15_internet_access_modes_clean.dta` and go to step 4.
- **The full BAHDA-2026 analytical microdata** (2,896 consented households, raw variable names). Build the
  analytical file first (step 3).

## 3. Build the analytical file (Stata, only if you have the raw file)

1. Copy the raw file to `p15_internet_access_modes/data/BAHDA2026_analytical_microdata.dta`, or edit the
   `global BAHDA_RAW` line at the top of `code/01_clean_p15.do` to point to it.
2. In Stata, change directory to `p15_internet_access_modes` and run `do code/01_clean_p15.do`.

The do-file keeps the outcome, the ten predictors and the design variables, recodes them to the codes in
Table 1, sets the expenditure answer "Prefer not to say" to missing, drops the 189 incomplete records and
asserts that 2,707 households remain. It saves `data/p15_internet_access_modes_clean.dta`. If an
`assert` fails, the source file differs from the one used for the paper.

## 4. Set up Python

Once you have been given access to the private repository:

```bash
git clone https://github.com/abdirahman108/amoud-bahda-analysis.git
cd amoud-bahda-analysis/p15_internet_access_modes
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

If you use different package versions, the estimates should still agree to the reported decimal places;
only the cross-validated penalised models (Table S5) can differ slightly, because their fold assignment
depends on scikit-learn's random number streams.

## 5. Run the analysis

```bash
cd code
bash run_all.sh
```

or step by step:

```bash
python3 run_analysis.py     # about 1 minute
python3 model_family.py     # about 2 minutes (penalised cross-validation)
python3 make_figures.py
python3 verify_outputs.py
```

`verify_outputs.py` prints one line per check and ends with `23 of 23 checks passed`. It exits with an
error if any value differs from the manuscript by more than its rounding tolerance.

## 6. Where each result comes from

All paths are relative to `p15_internet_access_modes/output/`.

| Manuscript item | Output file(s) | Script |
|---|---|---|
| Figure 1 (sample flow) | `figures/Figure1_sample_flow.png` | `make_figures.py` (counts from `01_clean_p15.do`) |
| Table 1 (variable definitions) | coding in `code/setup_data.py` and `code/01_clean_p15.do` | – |
| Outcome distribution, Section 3.3 | `tables/outcome_distribution_overall.csv`, `tables/outcome_by_residence.csv` | `run_analysis.py` |
| Figure 2 | `figures/Figure2_outcome_by_residence.png` | `make_figures.py` |
| Table 2 (characteristics and bivariate tests) | `tables/table2_characteristics_by_mode.csv`, `tables/table_bivariate_screening.csv` | `run_analysis.py` |
| Table 3 (survey-weighted multinomial model) | `tables/table3_full_model_rrr.csv`, `tables/table3_joint_wald.csv`, fit statistics in `results.json` (`full_info`) | `run_analysis.py` |
| Table 4 (average marginal effects) | `tables/table4_ame.csv` | `run_analysis.py` |
| Figure 3 (adjusted predictions) | `tables/adjusted_predictions.csv`, `figures/Figure3_adjusted_predictions.png` | `run_analysis.py`, `make_figures.py` |
| Diagnostics, Section 3.7 | `results.json` (`nonlinearity`, `accuracy_weighted`, `iia`), `tables/sparse_cells.csv`, `tables/diag_iia_hausman.csv`, `tables/classification_unweighted.csv` | `run_analysis.py` |
| Table S1 (missing data) | the Stata log of `01_clean_p15.do` | `01_clean_p15.do` |
| Table S2 (sensitivity analyses S0-S11) | `tables/tableS2_sensitivity.csv` | `run_analysis.py` |
| Table S3 (crude RRRs) | `tables/table_crude_rrr.csv` | `run_analysis.py` |
| Table S4 (VIF, GVIF, checklist) | `tables/table_vif_indicators.csv`, `tables/table_gvif.csv`, `results.json` | `run_analysis.py` |
| Table S5 (model comparison) | `tables/table5_model_comparison_sequential.csv`, `tables/table5_model_comparison_penalised.csv`, `tables/model_family/table5_model_family.csv` | `run_analysis.py`, `model_family.py` |
| Table S6 (alternative baseline) | `tables/tableS3_alt_baseline_smartphone.csv` | `run_analysis.py` |
| Supplementary Figure S1 (AMEs) | `figures/Figure4_average_marginal_effects.png` | `make_figures.py` |

In the CSV files, `outcome` codes are 0 = no internet access (reference), 1 = mobile data on a smartphone,
2 = mobile data on a feature phone, 3 = home Wi-Fi/fibre and 4 = public Wi-Fi/cyber café. Model terms are
written `variable=level` using the codes in Table 1. `rrr`, `lo` and `hi` are the relative risk ratio and its
95% confidence interval. `separated = True` marks the one parameter that cannot be estimated (no
peri-urban household used public Wi-Fi). AMEs are proportions, so multiply by 100 for percentage points.

## 7. Methods implemented in the code

- **Survey design.** Normalised weight `survey_weight`, six strata `sampling_stratum`, households as primary
  sampling units, Taylor-series linearised variance with 2,701 design degrees of freedom. This is equivalent
  to Stata `svyset record_id [pw = survey_weight], strata(sampling_stratum)`. Sensitivity analysis S1 uses
  the 64 urban sub-zone clusters as PSUs.
- **Bivariate tests.** The Rao-Scott second-order F test, identical to R
  `survey::svychisq(~x + y, design, statistic = "F")`. Continuous predictors use a design-based Wald F
  test, as in `survey::regTermTest`.
- **Primary model.** Survey-weighted multinomial logit with no internet access as the base outcome, fitted
  by Newton-Raphson pseudo-maximum likelihood (`svy.SvyMlogit`). This matches
  `svy: mlogit DV_internet_access_mode ..., baseoutcome(0) rrr` in Stata.
- **AMEs.** Differences in survey-weighted average predicted probabilities, with delta-method confidence
  intervals using the design-based covariance (`svy.margins`, `svy.contrast`).
- **Unweighted model family.** Multinomial logit (matches R `nnet::multinom` and Stata `mlogit`); ridge,
  lasso and elastic-net multinomial models with ten-fold cross-validated deviance; an alternative baseline;
  and two-part nominal logit and probit models. In these, part 1 separates home Wi-Fi/fibre from all other
  routes, and part 2 fits a multinomial logit among the remaining households.

## 8. Cross-checking with Stata

`code/02_analysis_p15.do` runs the same design, models, marginal effects and sensitivity checks in Stata.
From `p15_internet_access_modes`, run `do code/02_analysis_p15.do`. The point estimates and confidence
intervals should match `output/tables/table3_full_model_rrr.csv` and `table4_ame.csv` to the reported
decimals. For the peri-urban by public Wi-Fi cell, Stata reports the parameter as omitted or very large.
Python flags it as not estimable instead.

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| `FileNotFoundError: ... p15_internet_access_modes_clean.dta` | Place the data file as described in step 2. |
| `assert` fails in `01_clean_p15.do` | The source file is not the BAHDA-2026 release used for the paper. Check the version with the data custodian. |
| A Table S5 penalised-model value differs in the third decimal | This is expected with other scikit-learn versions; the other checks should still pass. |
| `verify_outputs.py` reports FAIL for other values | Check that the package versions match `requirements.txt` and that the data file has 2,707 rows. |

## 10. Contact

Abdirahman M. Abubakar, Amoud University, Borama, Somaliland. Email: abdirahman@amoud.edu.so.
ORCID: https://orcid.org/0009-0000-7075-7285
