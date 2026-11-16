version 16.0
set more off
* Optional: A Stata translation of the main parts of 2_run_analysis.py.
* It was not run for the revised manuscript. The independent check that the manuscript reports is
* r_crosscheck.R.
*
* Before you run it, make sure that data/borama_internet_access.dta exists. Then open Stata in the
* repository's main folder and run:
*     do scripts/stata_analysis.do
use "data/borama_internet_access.dta", clear

* Survey design: scaled weight, six strata, and each household as its own sampling unit
svyset record_id [pw = survey_weight], strata(sampling_stratum) vce(linearized)

gen head_age10 = head_age / 10
label variable head_age10 "Age of household head (per 10 years)"

* Describe the households (weighted %, 95% CI) and test each predictor with the Rao-Scott F test
svy: tabulate DV_internet_access_mode, percent ci
foreach v in residence head_sex head_education head_employment monthly_expenditure ///
    electricity_source smartphone youth_vocational_training {
    svy: tabulate `v' DV_internet_access_mode, row percent
}
foreach v in head_age household_size {
    svy: mean `v', over(DV_internet_access_mode)
    svy: regress `v' i.DV_internet_access_mode
    testparm i.DV_internet_access_mode
}

* Comparison groups as in Table 1 (for sex, male = 2 is the comparison group)
local A i.residence head_age10 ib2.head_sex ib1.head_education household_size
local B i.head_employment i.monthly_expenditure i.electricity_source i.youth_vocational_training
local C i.smartphone

* Models 1 to 3, each adding predictors. Model 3 is the main model. Each route is compared with no internet access.
svy: mlogit DV_internet_access_mode `A', baseoutcome(0) rrr
svy: mlogit DV_internet_access_mode `A' `B', baseoutcome(0) rrr
svy: mlogit DV_internet_access_mode `A' `B' `C', baseoutcome(0) rrr
foreach v in residence head_sex head_education head_employment monthly_expenditure ///
    electricity_source youth_vocational_training smartphone {
    testparm i.`v'
}
testparm head_age10
testparm household_size
* No peri-urban household used public Wi-Fi, so Stata reports that result as omitted or very large.
* The Python code marks it as not estimable. Both mean the same thing.

* Percentage-point differences (multiply by 100) and predicted percentages
margins, dydx(i.residence i.head_sex ib1.head_education i.head_employment i.monthly_expenditure ///
    i.electricity_source i.youth_vocational_training i.smartphone)
margins residence monthly_expenditure electricity_source smartphone

* Sensitivity analysis S1: urban sub-zones as the sampling units
gen str40 psu_cluster = cond(sampling_stratum <= 4 & trim(sub_zone) != "", ///
    "C_" + sub_zone, "H_" + string(record_id, "%15.0f"))
svyset psu_cluster [pw = survey_weight], strata(sampling_stratum)
svy: mlogit DV_internet_access_mode `A' `B' `C', baseoutcome(0) rrr
svyset record_id [pw = survey_weight], strata(sampling_stratum) vce(linearized)

* Sensitivity analysis S5: add five extra questions about household technology
svy: mlogit DV_internet_access_mode `A' `B' `C' i.head_marital_status i.primary_income_source ///
    i.basic_mobile i.computer_tablet i.head_digital_literacy, baseoutcome(0) rrr
