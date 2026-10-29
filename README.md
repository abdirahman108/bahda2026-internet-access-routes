# How households in Borama District access the internet (BAHDA-2026)

This repository holds the analysis code for the study *Ways Households Access the Internet in Borama
District, Somaliland: Evidence from the BAHDA-2026 Household Survey*. Starting from the survey file, it
produces every table, figure and number reported in the manuscript and its supplement. A final step
checks 23 key results automatically.

**Access.** The repository is private. Reviewers and researchers can request access from the
corresponding author (abdirahman@amoud.edu.so); please include your GitHub username. The household
microdata are not included (see [Data](#data)).

---

## Contents

1. [The study in brief](#the-study-in-brief)
2. [Repository layout](#repository-layout)
3. [Data](#data)
4. [How the pipeline works](#how-the-pipeline-works)
5. [How to reproduce](#how-to-reproduce)
6. [Where each result comes from](#where-each-result-comes-from)
7. [Methods implemented in the code](#methods-implemented-in-the-code)
8. [Cross-checking with Stata](#cross-checking-with-stata)
9. [Troubleshooting](#troubleshooting)
10. [Citation and contact](#citation-and-contact)

---

## The study in brief

The Borama Amoud Household Development Assessment (BAHDA) 2026 was a district-wide household survey
run by Amoud University in Borama District, Somaliland. It has 2,896 consented households across six
sampling strata: four urban, one peri-urban and one rural.

- **Question.** Which household and household-head characteristics are associated with the *main way*
  a household reaches the internet?
- **Outcome.** The main route to the internet, with five unordered categories: no internet access,
  mobile data on a smartphone, mobile data on a feature phone, home Wi-Fi/fibre, and public Wi-Fi or a
  cyber café.
- **Predictors.** Ten predictors, selected a priori:
  - residence (urban, peri-urban or rural);
  - the age, sex, education and employment of the household head;
  - household size and monthly expenditure;
  - electricity source and smartphone ownership;
  - vocational training among members aged 15–35.
- **Sample.** 2,707 households with complete data. The other 189 households answered "Prefer not to
  say" for expenditure.
- **Model.** A survey-weighted multinomial logistic regression with the normalised stratum weight and
  six strata. It reports relative risk ratios (RRRs) and average marginal effects (AMEs), and is
  checked by twelve sensitivity analyses.

## Repository layout

```
.
├── README.md                     this guide
├── requirements.txt              pinned Python packages
├── run_all.sh                    runs every step in order and checks the results
├── data/
│   └── README.md                 where to put the data file (the data are never committed)
├── scripts/                      the analysis, one numbered step per file
│   ├── 1_clean_data.do           Stata: raw BAHDA-2026 file -> analytical file (2,707 households)
│   ├── 2_run_analysis.py         survey-weighted analysis: Tables 2-4, sensitivity S0-S12, diagnostics
│   ├── 3_model_family.py         unweighted model family and model comparison (Table S5)
│   ├── 4_excluded_households.py  profile of the 189 excluded households (Table S1b)
│   ├── 5_make_figures.py         Figures 1-3 and Supplementary Figure S1
│   ├── 6_verify_outputs.py       compares a fresh run with the manuscript (23 checks)
│   ├── stata_analysis.do         Stata version of steps 2-3, for cross-checking
│   └── _paths.py                 lets the numbered scripts import from lib/
├── lib/                          shared code used by the scripts
│   ├── variables.py              variable codes, reference categories, model blocks, data loading
│   ├── svy.py                    design-based estimators (weights, strata, linearised variance)
│   └── atlas_margins.py          full-sample counts published in the BAHDA-2026 Atlas
└── outputs/                      created by the scripts (not tracked)
    ├── tables/                   CSV tables
    ├── figures/                  PNG figures
    └── results.json              key numbers quoted in the text
```

## Data

The BAHDA-2026 household microdata are held by Amoud University and are not redistributed, because they
contain confidential household records. Access is through the Amoud University Research and Innovation
Center under its data-governance procedures.

`.gitignore` excludes every `.dta` file and everything in `data/` except its README, so a data file
cannot be committed by accident.

You will receive one of two files:

| File | Contents | What to do |
|---|---|---|
| Analytical extract | 2,707 households, 21 variables, including `DV_internet_access_mode` | Save it as `data/borama_internet_access.dta` and go to step 4 of [How to reproduce](#how-to-reproduce). |
| Full BAHDA-2026 analytical microdata | 2,896 consented households, raw variable names | Build the extract first with `scripts/1_clean_data.do` (step 3). |

The published aggregate results are in the BAHDA-2026 Atlas (https://doi.org/10.67178/pgc3n7h0).
`lib/atlas_margins.py` copies the full-sample counts from the Atlas tables that step 4 of the pipeline
needs, with the table number of each.

## How the pipeline works

1. **Clean** (`1_clean_data.do`, Stata):
   - keeps the outcome, the ten predictors, five extra household ICT items and the design variables;
   - recodes them to the codes in the manuscript's Table 1;
   - sets the expenditure answer "Prefer not to say" to missing and drops those 189 records;
   - asserts that 2,707 households with positive weights and unique identifiers remain.
2. **Analyse** (`2_run_analysis.py`):
   - survey-weighted descriptive statistics and Rao–Scott tests;
   - multicollinearity checks;
   - three nested survey-weighted multinomial models, with AMEs and adjusted predictions;
   - diagnostics: linearity, IIA, influence, classification, effective sample size;
   - sensitivity analyses S0–S12 and penalised models.
3. **Model family** (`3_model_family.py`): unweighted multinomial logit; ridge, lasso and elastic-net
   models with cross-validated deviance; an alternative baseline; two-part logit and probit models.
4. **Excluded households** (`4_excluded_households.py`): the extract does not contain the 189 excluded
   households. The script recovers their distribution on every analysis variable by subtracting the
   extract's counts from the Atlas's full-sample counts.
   - As a check, their reconstructed weights add up to 190.6, the Atlas's weighted count for "Prefer
     not to say".
   - `lib/atlas_margins.py` also rakes the weights to the full-sample margins; sensitivity S12 in step 2
     uses those weights.
5. **Figures** (`5_make_figures.py`): Figures 1–3 and Supplementary Figure S1.
6. **Verify** (`6_verify_outputs.py`): compares 23 key results with the values printed in the
   manuscript, within rounding.

## How to reproduce

A full run takes about four minutes on a laptop.

### 1. Requirements

| Item | Notes |
|---|---|
| Python 3.11 or newer | Results were produced with Python 3.13 and the versions in `requirements.txt`. |
| Stata 16 or newer (optional) | Needed only to build the extract from the full file, or to run the Stata cross-check. |
| git | To clone the repository after you have been given access. |
| The data file | See [Data](#data). |

### 2. Get the code and the data

```bash
git clone https://github.com/abdirahman108/bahda2026-internet-access-routes.git
cd bahda2026-internet-access-routes
```

Copy the analytical extract to `data/borama_internet_access.dta`. If you have the full file instead,
do step 3 first.

### 3. Build the analytical file (only if you have the full microdata)

1. Copy the full file to `data/BAHDA2026_analytical_microdata.dta`, or edit the `global BAHDA_RAW` line
   at the top of `scripts/1_clean_data.do`.
2. In Stata, from the repository root, run `do scripts/1_clean_data.do`.

The script saves `data/borama_internet_access.dta`. If one of its `assert` lines fails, your source
file differs from the release used for the manuscript.

### 4. Set up Python

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Run everything

```bash
bash run_all.sh
```

The last lines should read `23 of 23 checks passed`. To run the steps one at a time, from the
repository root:

```bash
python3 scripts/2_run_analysis.py        # about 1 minute
python3 scripts/3_model_family.py        # about 2 minutes (cross-validation)
python3 scripts/4_excluded_households.py
python3 scripts/5_make_figures.py
python3 scripts/6_verify_outputs.py
```

**Expected variation.** With other package versions the estimates agree to the reported decimals.
The cross-validated lasso and elastic-net models (Table S5) are the exception: their solver is
stochastic, so their third decimal can vary between runs and machines.

## Where each result comes from

Paths are relative to `outputs/`.

| Manuscript item | Output file(s) | Script |
|---|---|---|
| Figure 1 (sample flow) | `figures/Figure1_sample_flow.png` | `5_make_figures.py` (counts from `1_clean_data.do`) |
| Table 1 (variable definitions) | coding in `lib/variables.py` and `scripts/1_clean_data.do` | – |
| Outcome distribution (Section 3.3) | `tables/outcome_distribution_overall.csv`, `tables/outcome_by_residence.csv` | `2_run_analysis.py` |
| Figure 2 | `figures/Figure2_outcome_by_residence.png` | `5_make_figures.py` |
| Table 2 (characteristics, bivariate tests) | `tables/table2_characteristics_by_mode.csv`, `tables/table_bivariate_screening.csv` | `2_run_analysis.py` |
| Table 3 (multinomial model) | `tables/table3_full_model_rrr.csv`, `tables/table3_joint_wald.csv`; fit statistics in `results.json` (`full_info`) | `2_run_analysis.py` |
| Model 2 (without smartphone ownership) | `tables/table_model2_rrr.csv` | `2_run_analysis.py` |
| Table 4 (average marginal effects) | `tables/table4_ame.csv` | `2_run_analysis.py` |
| Figure 3 (adjusted predictions) | `tables/adjusted_predictions.csv`, `figures/Figure3_adjusted_predictions.png` | `2_run_analysis.py`, `5_make_figures.py` |
| Diagnostics (Section 3.7) | `results.json` (`nonlinearity`, `iia`, `kish_deff`, `kish_neff`, `events_per_parameter`), `tables/sparse_cells.csv`, `tables/diag_iia_hausman.csv` | `2_run_analysis.py` |
| Table S1 (missing data) | the log of `1_clean_data.do` | `1_clean_data.do` |
| Table S1b (excluded vs included) | `tables/tableS1b_excluded_vs_included.csv`, `tables/tableS1b_tests.csv`, `excluded_profile.json` | `4_excluded_households.py` |
| Table S2 (sensitivity analyses S0–S12) | `tables/tableS2_sensitivity.csv` | `2_run_analysis.py` |
| Table S3 (crude RRRs) | `tables/table_crude_rrr.csv` | `2_run_analysis.py` |
| Table S4 (VIF, GVIF, checklist) | `tables/table_vif_indicators.csv`, `tables/table_gvif.csv`, `results.json` | `2_run_analysis.py` |
| Table S5 (model comparison) | `tables/table5_model_comparison_sequential.csv`, `tables/table5_model_comparison_penalised.csv`, `tables/model_family/table5_model_family.csv` | `2_run_analysis.py`, `3_model_family.py` |
| Table S6 (alternative baseline) | `tables/tableS3_alt_baseline_smartphone.csv` | `2_run_analysis.py` |
| Table S7 (observed vs predicted route) | `tables/classification_unweighted.csv` | `2_run_analysis.py` |
| Supplementary Figure S1 (AMEs) | `figures/FigureS1_average_marginal_effects.png` | `5_make_figures.py` |

**How to read the CSV files:**
- `outcome` codes: 0 = no internet access (reference), 1 = smartphone data, 2 = feature-phone data,
  3 = home Wi-Fi/fibre, 4 = public Wi-Fi/cyber café.
- Model terms are written `variable=level`, using the codes in Table 1.
- `rrr`, `lo` and `hi` are the relative risk ratio and its 95% confidence interval.
- `separated = True` marks the one parameter that cannot be estimated (no peri-urban household used
  public Wi-Fi).
- AMEs are proportions; multiply by 100 for percentage points.

## Methods implemented in the code

- **Survey design.** The design uses:
  - the normalised weight `survey_weight` and six strata `sampling_stratum`;
  - households as primary sampling units;
  - Taylor-series linearised variance with 2,701 design degrees of freedom.

  This is equivalent to Stata `svyset record_id [pw = survey_weight], strata(sampling_stratum)`.
  Sensitivity S1 uses the 64 urban sub-zone clusters as primary sampling units instead.
- **Bivariate tests.** The Rao–Scott second-order F test, which matches R
  `survey::svychisq(~x + y, design, statistic = "F")`. Continuous predictors use a design-based Wald F
  test.
- **Primary model.** A survey-weighted multinomial logit with no internet access as the base outcome,
  fitted by pseudo-maximum likelihood (`lib/svy.py`, `SvyMlogit`). It matches Stata
  `svy: mlogit DV_internet_access_mode ..., baseoutcome(0) rrr`.
- **AMEs.** Differences in survey-weighted average predicted probabilities, with delta-method
  confidence intervals from the design-based covariance.
- **Sensitivity analyses** (S0 is the primary model):

  | Run | What changes |
  |---|---|
  | S1 | Cluster primary sampling units |
  | S2 | Unweighted |
  | S3 | Households with education not reported dropped (complete case) |
  | S4 | Smartphone ownership removed |
  | S5 | Five extra ICT items added |
  | S6 | Influential households removed |
  | S7 | Wi-Fi categories merged |
  | S8 | Ridge penalty |
  | S9 | Public Wi-Fi dropped |
  | S10 | Mobile-data routes merged |
  | S11 | Weights capped at 3 |
  | S12 | Weights raked to the full-sample margins |

- **Effective sample size.** The Kish design effect from unequal weighting is 2.61, so the effective
  sample size is about 1,040.

## Cross-checking with Stata

From the repository root, run `do scripts/stata_analysis.do`. It runs the same design, models, marginal
effects and sensitivity checks in Stata. Point estimates and confidence intervals should match
`outputs/tables/table3_full_model_rrr.csv` and `table4_ame.csv` to the reported decimals.

The one difference is the peri-urban by public Wi-Fi cell: Stata reports that parameter as omitted or
very large, while the Python code flags it as not estimable.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Missing data/borama_internet_access.dta` | Place the data file as described in [Data](#data). |
| An `assert` fails in `1_clean_data.do` | The source file is not the release used for the manuscript; check the version with the data custodian. |
| A lasso or elastic-net value in Table S5 differs in the third decimal | Expected (stochastic solver); the 23 checks still pass. |
| `6_verify_outputs.py` reports FAIL for another value | Check the package versions against `requirements.txt`, and check that the data file has 2,707 rows. |

## Citation and contact

Please cite the manuscript, and the survey: Amoud University (2026), *BAHDA-2026 Atlas*,
https://doi.org/10.67178/pgc3n7h0.

Abdirahman M. Abubakar, Faculty of ICT, Amoud University, Borama, Somaliland.
Email: abdirahman@amoud.edu.so. ORCID: https://orcid.org/0009-0000-7075-7285.
