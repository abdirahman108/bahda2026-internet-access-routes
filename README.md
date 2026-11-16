# How households in Borama District access the internet (BAHDA-2026)

This repository contains the analysis code for the following manuscript:

*Factors associated with the main route of household internet access in Borama District, Somaliland:
a cross-sectional analysis of the BAHDA-2026 household survey*

The code starts from the survey data file. It produces every table, figure, and number in the manuscript
and its supplement. Its last step compares 21 key results with the values printed in the manuscript.

This guide is for reviewers and other researchers who want to check or reproduce the results. You don't
need a background in statistics or programming to follow the steps in
[Reproduce the results](#reproduce-the-results).

> **Note:** The household survey data aren't included in this repository. To learn how to get the data,
> see [About the data](#about-the-data).

## On this page

1. [About the study](#about-the-study)
2. [What's in this repository](#whats-in-this-repository)
3. [About the data](#about-the-data)
4. [What the code does](#what-the-code-does)
5. [Reproduce the results](#reproduce-the-results)
6. [Find the source of each result](#find-the-source-of-each-result)
7. [Methods used in the code](#methods-used-in-the-code)
8. [Check the results in Stata](#check-the-results-in-stata)
9. [Troubleshooting](#troubleshooting)
10. [Glossary](#glossary)
11. [Cite this work and contact us](#cite-this-work-and-contact-us)

## About the study

In 2026, Amoud University surveyed households across Borama District, Somaliland. The survey is
called the Borama Amoud Household Development Assessment (BAHDA) 2026. It covers 2,896 households that
agreed to take part, in six areas called *strata*: four urban, one peri-urban, and one rural.

The study asks one question: which characteristics of a household, and of the person who heads it,
are linked to the main way that the household reaches the internet?

The study uses the following information:

- **What it explains (the outcome).** The household's main route to the internet. There are five
  possible answers, in no particular order:
  - No internet access
  - Mobile data on a smartphone
  - Mobile data on a basic (feature) phone
  - Home Wi-Fi or fibre
  - Public Wi-Fi or a cyber café
- **What it uses to explain it (the predictors).** Ten characteristics, chosen before the analysis
  began:
  - Where the household lives: urban, peri-urban, or rural
  - The age, sex, education, and employment of the head of the household
  - The number of people in the household
  - The household's monthly spending
  - The household's main source of electricity
  - Whether the household owns a smartphone
  - Whether any member aged 15 to 35 has completed vocational training
- **Which households it includes.** 2,707 households with complete answers. The other 189 households
  have no stated monthly spending, so they're left out. The Atlas lists them as "Prefer not to say". The
  data office describes the group as answers affected by skip logic, non-response, or "Prefer not to say".
- **How it analyses them.** A regression model built for survey data with more than two unordered
  answers. The model gives each household a *survey weight* so that the results describe the whole
  district, not only the households that were interviewed. Fifteen extra analyses, called
  *sensitivity analyses*, check whether the main results change when the method changes.

For definitions of the statistical terms, see the [Glossary](#glossary).

## What's in this repository

The following tree shows the main files and folders:

```
.
├── README.md                     This guide.
├── requirements.txt              The Python packages and the exact versions to install.
├── run_all.sh                    Runs every step in order and checks the results.
├── data/
│   └── README.md                 Where to put the data file. Data files are never saved to the repository.
├── scripts/                      The analysis, one numbered step per file.
│   ├── 1_clean_data.do           Step 1 (Stata): turns the full survey file into the analysis file.
│   ├── 2_run_analysis.py         Step 2: the main analysis, Tables 2 to 4, and the sensitivity analyses.
│   ├── 4_excluded_households.py  Step 4: describes the 189 households left out (Table S2).
│   ├── 5_make_figures.py         Step 5: Figures 1 to 3 and Supplementary Figure S1.
│   ├── 6_verify_outputs.py       Step 6: compares 21 results with the manuscript.
│   ├── r_crosscheck.R            Optional: fits the main model again in R, as an independent check.
│   ├── 7_compare_r.py            Optional: compares the R results with the Python results.
│   ├── stata_analysis.do         Optional: runs steps 2 and 3 in Stata, so you can compare.
│   └── _paths.py                 Lets the scripts find the shared code in lib/.
├── lib/                          Code that the scripts share.
│   ├── variables.py              Names, codes, and comparison groups for every variable; loads the data.
│   ├── svy.py                    The survey statistics: weights, strata, and confidence intervals.
│   └── atlas_margins.py          Totals for all 2,896 households, copied from the BAHDA-2026 Atlas.
├── revision_outputs/             The tables and figures behind the revised manuscript (run of 14 November 2026).
└── outputs/                      Created when you run the code. Not saved to the repository.
    ├── tables/                   Tables, as CSV files.
    ├── figures/                  Figures, as PNG images.
    └── results.json              Key numbers quoted in the manuscript text.
```

## About the data

Amoud University holds the BAHDA-2026 household survey data. The data contain confidential household
records, so they aren't shared publicly or stored in this repository. To request a de-identified analysis file, contact
the Directorate of Research Strategy, Development and Performance (RSDP), Amoud University, Borama,
which releases data under the university's data-governance conditions.

The repository's `.gitignore` file blocks every Stata data file (`.dta`) and everything in the `data/`
folder except its README. This setting stops anyone from saving a data file to the repository by
mistake.

You receive one of the following two files. The table shows what to do with each.

| File you receive | What it contains | What to do |
|---|---|---|
| Analysis file | 2,707 households and 21 variables, including `DV_internet_access_mode` | Save it as `data/borama_internet_access.dta`, and then go to [step 4 of Reproduce the results](#4-set-up-python). |
| Full survey file | 2,896 households, with the survey's original variable names | First build the analysis file. See [step 3 of Reproduce the results](#3-optional-build-the-analysis-file-from-the-full-survey-file). |

The survey's published results are in the
[BAHDA-2026 Atlas](https://doi.org/10.67178/pgc3n7h0). The file `lib/atlas_margins.py` copies the
totals for all 2,896 households from the Atlas tables that step 4 of the analysis needs. Each total
lists the number of the Atlas table that it comes from.

## What the code does

The analysis runs in five steps. Each step is one file in the `scripts/` folder. There is no step 3:
it fitted alternative models without survey weights, which the revised manuscript no longer reports.

1. **Clean the data** (`1_clean_data.do`, in Stata). This step does the following:
   - Keeps the outcome, the ten predictors, five extra questions about household technology, and the
     survey design variables.
   - Recodes each variable to the codes in Table 1 of the manuscript.
   - Removes the 189 households with no stated monthly spending.
   - Confirms that 2,707 households remain, each with a valid weight and a unique ID.
2. **Run the main analysis** (`2_run_analysis.py`). This step does the following:
   - Describes the households, using the survey weights, and tests how each characteristic relates to
     the outcome.
   - Checks that no two predictors measure the same thing.
   - Fits three models, each adding a group of predictors to the one before.
   - Converts the results into percentage-point differences and predicted percentages.
   - Runs checks on how well the model fits.
   - Tests each added group of predictors with an adjusted Wald test.
   - Runs the fifteen sensitivity analyses (S1 to S15 in the code; SA1 to SA15 in the manuscript).
   - Works out how much larger each standard error could be before a result stopped being
     statistically significant (the clustering margin).
4. **Describe the households left out** (`4_excluded_households.py`). The analysis file doesn't
   contain the 189 households that were left out. This step works out their characteristics by
   subtracting the analysis file's counts from the Atlas's counts for all 2,896 households.
   - As a check, the left-out households' weights add up to 190.6. This total is the Atlas's
     weighted count for its "Prefer not to say" row, so the subtraction is correct.
   - The file `lib/atlas_margins.py` also adjusts the survey weights so that the 2,707 households
     match the Atlas totals for all 2,896 households. Sensitivity analysis S12 in step 2 uses these
     adjusted weights.
5. **Draw the figures** (`5_make_figures.py`). Draws Figures 1 to 3 and Supplementary Figure S1.
6. **Check the results** (`6_verify_outputs.py`). Compares 21 key results with the values printed in
   the manuscript, allowing for rounding.

## Reproduce the results

A full run takes about four minutes on a laptop.

### Before you begin

Make sure that you have the following:

| What you need | Details |
|---|---|
| Python 3.11 or later | The published results used Python 3.13 and the package versions in `requirements.txt`. |
| Stata 16 or later (optional) | You need Stata only to build the analysis file from the full survey file, or to [check the results in Stata](#check-the-results-in-stata). |
| Git | You use Git to download the repository after you're given access. |
| The data file | See [About the data](#about-the-data). |

### 1. Download the code

In a terminal, run the following commands:

```bash
git clone https://github.com/abdirahman108/bahda2026-internet-access-routes.git
cd bahda2026-internet-access-routes
```

### 2. Add the data file

Copy the analysis file to `data/borama_internet_access.dta`.

If you have the full survey file instead, go to step 3.

### 3. (Optional) Build the analysis file from the full survey file

Do this step only if you have the full survey file.

1. Copy the full survey file to `data/BAHDA2026_analytical_microdata.dta`.

   If your file is somewhere else, change the `global BAHDA_RAW` line at the top of
   `scripts/1_clean_data.do` to point to it.
2. Open Stata, and change to the repository's main folder.
3. Run the following command:

   ```stata
   do scripts/1_clean_data.do
   ```

The script saves `data/borama_internet_access.dta`. If the script stops at an `assert` line, your file
isn't the version used for the manuscript.

### 4. Set up Python

Run the following commands. They create a separate Python environment and install the exact package
versions used for the manuscript.

```bash
python3 -m venv .venv
source .venv/bin/activate            # On Windows, run .venv\Scripts\activate instead.
pip install -r requirements.txt
```

### 5. Run the analysis

From the repository's main folder, run the following command:

```bash
bash run_all.sh
```

When the run finishes, the last line reads `21 of 21 checks passed`.

To run the steps one at a time instead, run the following commands in this order:

```bash
python3 scripts/2_run_analysis.py        # About 1 minute.
python3 scripts/4_excluded_households.py
python3 scripts/5_make_figures.py
python3 scripts/6_verify_outputs.py
```

### Results that can vary slightly

If you use other package versions, your results still match the manuscript to the decimal places it
reports.

## Find the source of each result

The following table shows which file holds each result in the manuscript, and which script creates
it. File paths are relative to the `outputs/` folder.

| Manuscript item | Output file | Script |
|---|---|---|
| Figure 1 (how the sample was selected) | `figures/Figure1_sample_flow.png` | `5_make_figures.py`, using counts from `1_clean_data.do` |
| Table 1 (variable definitions) | The coding in `lib/variables.py` and `scripts/1_clean_data.do` | None |
| How many households use each route (Section 3.3) | `tables/outcome_distribution_overall.csv`, `tables/outcome_by_residence.csv` | `2_run_analysis.py` |
| Figure 2 (routes by area) | `figures/Figure2_outcome_by_residence.png` | `5_make_figures.py` |
| Table 2 (household characteristics by route) | `tables/table2_characteristics_by_mode.csv`, `tables/table_bivariate_screening.csv` | `2_run_analysis.py` |
| Table 3 (main model) | `tables/table3_full_model_rrr.csv`, `tables/table3_joint_wald.csv`, and the `full_info` entry in `results.json` | `2_run_analysis.py` |
| Model 2 (the main model without smartphone ownership) | `tables/table_model2_rrr.csv` | `2_run_analysis.py` |
| Table 4 (percentage-point differences) | `tables/table4_ame.csv` | `2_run_analysis.py` |
| Figure 3 (predicted percentages) | `tables/adjusted_predictions.csv`, `figures/Figure3_adjusted_predictions.png` | `2_run_analysis.py`, `5_make_figures.py` |
| Table S1 (missing answers) | The log that `1_clean_data.do` prints | `1_clean_data.do` |
| Table S2 (households left out compared with those included) | `tables/tableS1b_excluded_vs_included.csv`, `tables/tableS1b_tests.csv`, `excluded_profile.json` | `4_excluded_households.py` |
| Tables S3 and S4 (sensitivity analyses SA1 to SA15) | `tables/tableS2_sensitivity.csv` | `2_run_analysis.py` |
| Table S5 (each predictor on its own) | `tables/table_crude_rrr.csv` | `2_run_analysis.py` |
| Table S6 (Model 2, without smartphone ownership) | `tables/table_model2_rrr.csv` | `2_run_analysis.py` |
| Table S7 (education with the Missing/unspecified group as the comparison group) | `tables/tableS_education_alt_reference.csv` | `2_run_analysis.py` |
| Table S8 (counts and confidence intervals for every cell of Table 2) | `tables/tableS_table2_row_ci.csv` | `2_run_analysis.py` |
| Table S9 (model comparison and Wald tests) | `tables/table5_information_criteria.csv`, `tables/table_block_wald.csv`, `tables/table3_joint_wald.csv`, `tables/table5_model_comparison_sequential.csv` | `2_run_analysis.py` |
| Table S10 (overlap between predictors) | `tables/table_vif_indicators.csv`, `tables/table_gvif.csv` | `2_run_analysis.py` |
| Table S11 (model checks) | The `nonlinearity`, `iia`, `kish_deff`, `kish_neff`, and `events_per_parameter` entries in `results.json`; `tables/sparse_cells.csv`; `tables/diag_iia_hausman.csv` | `2_run_analysis.py` |
| Table S12 (smartphone data as the comparison route) | `tables/tableS3_alt_baseline_smartphone.csv` | `2_run_analysis.py` |
| Table S13 (actual compared with predicted route) | `tables/classification_unweighted.csv` | `2_run_analysis.py` |
| Table S14 (clustering margin) | `tables/table_clustering_margin.csv` | `2_run_analysis.py` |
| Table S15 (Python compared with R) | `tables/tableS_software_agreement.csv`, `tables/r_crosscheck_coefficients.csv` | `r_crosscheck.R`, `7_compare_r.py` |
| Household size in four groups (SA14) | `tables/tableS_household_size_groups.csv` | `2_run_analysis.py` |
| Supplementary Figure S1 (percentage-point differences) | `figures/FigureS1_average_marginal_effects.png` | `5_make_figures.py` |

### Read the CSV files

The CSV files use the following conventions:

- The `outcome` column uses these codes:
  - `0`: No internet access. The model compares every other route with this one.
  - `1`: Mobile data on a smartphone.
  - `2`: Mobile data on a feature phone.
  - `3`: Home Wi-Fi or fibre.
  - `4`: Public Wi-Fi or a cyber café.
- The `term` column names a predictor and its level as `variable=level`, using the codes in Table 1.
  For example, `residence=2` means peri-urban, compared with urban.
- The `rrr`, `lo`, and `hi` columns are the relative risk ratio and the lower and upper ends of its 95%
  confidence interval.
- `separated = True` marks the one result that can't be estimated, because no peri-urban household
  used public Wi-Fi.
- The `ame` column is a proportion. To get percentage points, multiply it by 100.

## Methods used in the code

This section is for readers who want the statistical details.

- **Survey design.** The code accounts for how the survey was sampled. It uses the following:
  - The survey weight, `survey_weight`, scaled so that the weights add up to the number of households.
  - The six strata, `sampling_stratum`.
  - Each household as its own sampling unit.
  - Taylor-series linearisation for confidence intervals, with 2,701 design degrees of freedom.

  This setup matches the Stata command
  `svyset record_id [pw = survey_weight], strata(sampling_stratum)`. Sensitivity analysis S1 uses the
  64 urban sub-zones as sampling units instead. Sub-zones stand in for the survey clusters, whose
  identifiers are not in the analysis file.
- **Tests between two variables.** The code uses the Rao–Scott second-order F test, which matches the
  R command `survey::svychisq(~x + y, design, statistic = "F")`. For predictors that are numbers, such
  as age, it uses a design-based Wald F test.
- **Main model.** A survey-weighted multinomial logistic regression. It compares each route with no
  internet access, and it's fitted by pseudo-maximum likelihood (`SvyMlogit` in `lib/svy.py`). It
  matches the Stata command `svy: mlogit DV_internet_access_mode ..., baseoutcome(0) rrr`.
- **Percentage-point differences.** Average marginal effects (AMEs): the difference in the
  survey-weighted average predicted probability between two groups. Their confidence intervals use
  the delta method with the survey-based covariance.
- **Sensitivity analyses.** S0 is the main model. Each of the others changes one thing, as the
  following table shows:

  | Analysis | What changes |
  |---|---|
  | S1 | Urban sub-zones are the sampling units. |
  | S2 | No survey weights. |
  | S3 | Households whose head's education is classified Missing/unspecified are left out. |
  | S4 | Smartphone ownership is removed. |
  | S5 | Five extra questions about household technology are added. |
  | S6 | The 1% of households with the most influence on the results are removed. |
  | S7 | Home Wi-Fi and public Wi-Fi are combined into one route. |
  | S8 | A ridge penalty shrinks the estimates. |
  | S9 | Households that use public Wi-Fi are left out. |
  | S10 | The two mobile-data routes are combined. |
  | S11 | Survey weights are capped at 3. |
  | S12 | The weights are adjusted to match the Atlas totals for all 2,896 households. |
  | S13 | The Missing/unspecified education group is the comparison group. |
  | S14 | Household size is entered in four groups (1 to 5, 6 to 8, 9 to 11, 12 or more). |
  | S15 | The two highest spending bands are combined (US$600 or more). |

  The manuscript calls these analyses SA1 to SA15.

- **Effective sample size.** Because the weights vary, the 2,707 households carry the same
  statistical information as 1,039 households with equal weights. The Kish design effect is 2.606.

## Check the results in R

The main model was fitted a second time in R, as an independent check. You need R 4.6 or later with the
packages `haven`, `survey`, `VGAM`, and `svyVGAM`. From the repository's main folder, run:

```bash
Rscript scripts/r_crosscheck.R
python3 scripts/7_compare_r.py
```

The second command writes `outputs/tables/tableS_software_agreement.csv`. In the run behind the revised
manuscript (R 4.6.2, survey 4.5, svyVGAM 1.3), all 87 coefficients that can be estimated agreed with the
Python results to at least six decimal places.

## Check the results in Stata

You can check the Python results with Stata. From the repository's main folder, run the following
command in Stata:

```stata
do scripts/stata_analysis.do
```

The script is a Stata translation of the survey design, the three models, the percentage-point
differences, and sensitivity analyses S1 and S5. It wasn't run for the revised manuscript, so treat it
as a starting point and not as a verified check. The R check above is the independent check that the
manuscript reports.

There is one expected difference. For peri-urban households and public Wi-Fi, Stata reports the result
as omitted or very large. The Python code marks it as not estimable instead. Both mean the same thing:
no peri-urban household used public Wi-Fi.

## Troubleshooting

| Problem | Solution |
|---|---|
| The message `Missing data/borama_internet_access.dta` appears. | Put the data file in the `data/` folder. See [About the data](#about-the-data). |
| `1_clean_data.do` stops at an `assert` line. | Your survey file isn't the version used for the manuscript. Ask the data custodian which version you have. |
| `6_verify_outputs.py` reports `FAIL` for any other value. | Check that your package versions match `requirements.txt`, and that the data file has 2,707 rows. |

## Glossary

The following table explains the statistical terms used in this guide and in the manuscript.

| Term | Meaning |
|---|---|
| Average marginal effect (AME) | How much more or less likely, in percentage points, one group is to use a route than the comparison group, after taking the other predictors into account. |
| Confidence interval (CI) | The range of values that is consistent with the data. A 95% confidence interval is built so that, in repeated surveys, 95% of such intervals would contain the true value. |
| Multinomial logistic regression | A model for an outcome with more than two answers that have no natural order. It compares each answer with one reference answer. Here, the reference answer is no internet access. |
| Reference category | The comparison group for a predictor. For example, urban households are the reference for residence, and primary education is the reference for education. |
| Relative risk ratio (RRR) | How much more likely a group is than the reference group to use a route rather than have no internet access. A value above 1 means more likely, and a value below 1 means less likely. |
| Sensitivity analysis | A repeat of the analysis with one choice changed, to check whether the main results depend on that choice. |
| Stratum (plural: strata) | One of the six areas that the survey sampled separately: four urban, one peri-urban, and one rural. |
| Survey weight | A number given to each household so that the results represent the whole district. Households in areas that were sampled less heavily get larger weights. |

## Cite this work and contact us

If you use this code, cite the manuscript and the survey. Citation details for the code are in
`CITATION.cff`.

Amoud University. (2026). *BAHDA-2026 Atlas*. https://doi.org/10.67178/pgc3n7h0

For questions, contact the corresponding author:

Abdirahman M. Abubakar, Faculty of ICT, Amoud University, Borama, Somaliland\
Email: abdirahman@amoud.edu.so\
ORCID: https://orcid.org/0009-0000-7075-7285
