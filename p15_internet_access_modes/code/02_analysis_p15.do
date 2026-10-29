version 16.0
set more off
* Paper 15: Ways households access the internet in Borama District (BAHDA-2026)
* Stata equivalent of run_analysis.py (primary analysis) and model_family.py.
* Run from the repository folder p15_internet_access_modes after 01_clean_p15.do.
* Predictors: the ten variables of the BAHDA-2026 ICT title and variable
* alignment sheet (IV1-IV10).
use "data/p15_internet_access_modes_clean.dta", clear

* Survey design: normalised weight, six strata, households as PSUs
svyset record_id [pw = survey_weight], strata(sampling_stratum) vce(linearized)

gen head_age10 = head_age / 10
label variable head_age10 "Age of household head (per 10 years)"

* Descriptives (weighted %, 95% CI) and Rao-Scott second-order F tests
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

* Reference categories as in Table 1 (sex: male = 2 is the base)
local A i.residence head_age10 ib2.head_sex i.head_education household_size
local B i.head_employment i.monthly_expenditure i.electricity_source i.youth_vocational_training
local C i.smartphone

* Sequential models; Model 3 is the primary model (base outcome = no internet access)
svy: mlogit DV_internet_access_mode `A', baseoutcome(0) rrr
svy: mlogit DV_internet_access_mode `A' `B', baseoutcome(0) rrr
svy: mlogit DV_internet_access_mode `A' `B' `C', baseoutcome(0) rrr
foreach v in residence head_sex head_education head_employment monthly_expenditure ///
    electricity_source youth_vocational_training smartphone {
    testparm i.`v'
}
testparm head_age10
testparm household_size
* Peri-urban x public Wi-Fi is an empty cell: Stata will report the parameter as
* omitted or with an extreme estimate (quasi-separation), as in the paper.

* Average marginal effects (percentage points = x100) and adjusted predictions
margins, dydx(i.residence i.head_sex i.head_education i.head_employment i.monthly_expenditure ///
    i.electricity_source i.youth_vocational_training i.smartphone)
margins residence monthly_expenditure electricity_source smartphone

* Sensitivity S1: urban sub-zone clusters as PSUs
gen str40 psu_cluster = cond(sampling_stratum <= 4 & trim(sub_zone) != "", ///
    "C_" + sub_zone, "H_" + string(record_id, "%15.0f"))
svyset psu_cluster [pw = survey_weight], strata(sampling_stratum)
svy: mlogit DV_internet_access_mode `A' `B' `C', baseoutcome(0) rrr
svyset record_id [pw = survey_weight], strata(sampling_stratum) vce(linearized)

* Sensitivity S5: five further household ICT items added
svy: mlogit DV_internet_access_mode `A' `B' `C' i.head_marital_status i.primary_income_source ///
    i.basic_mobile i.computer_tablet i.head_digital_literacy, baseoutcome(0) rrr

* Unweighted model family (Supplementary Table S5); raw age, lowest code as reference
local X i.residence i.head_sex i.head_education i.monthly_expenditure i.smartphone ///
    i.electricity_source i.head_employment i.youth_vocational_training c.head_age c.household_size
mlogit DV_internet_access_mode `X', baseoutcome(0)
estat ic
mlogit DV_internet_access_mode `X', baseoutcome(1)
* two-part nominal models: part 1 home Wi-Fi/fibre vs any other route, part 2 among the rest
gen byte homewifi = DV_internet_access_mode == 3
logit homewifi `X'
scalar ll_logit = e(ll)
probit homewifi `X'
scalar ll_probit = e(ll)
mlogit DV_internet_access_mode `X' if DV_internet_access_mode != 3, baseoutcome(0)
display "two-part logit LL = " ll_logit + e(ll) "   two-part probit LL = " ll_probit + e(ll)
