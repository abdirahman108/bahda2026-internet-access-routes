version 16.0
set more off
* Paper 15: Ways households access the internet in Borama District: Evidence from the BAHDA 2026 Household Survey
* Researcher: 15 Abdirahman Mohamed Haji Abubakar
* Run from the repository folder p15_internet_access_modes.
* Input: the authorised BAHDA-2026 analytical microdata (raw variable names,
* 2,896 consented households). It is not distributed with this repository;
* set the path below to your local copy before running.
global BAHDA_RAW "data/BAHDA2026_analytical_microdata.dta"
use "$BAHDA_RAW", clear

* 1. Keep the selected paper variables plus record ID, weight and stratum.
keep what_is_the_main_way_your_ residence3 v102 v101 v106 v_902_roughly_what_was_you v114 v1001 v104 v121 has_any_household_member_1 does_your_household_own_a__002 how_would_you_rate_the_dig v113 v103 v_901_what_is_the_primary_ id wgt bahda_strata_code v_002_zone v_003_sub_zone

* 2. Recode by SOURCE VALUE LABELS, before removing missing values.
* Education None is a valid No schooling category (0), not missing.
recode what_is_the_main_way_your_ (1 = 3) (2 = 2) (3 = 1) (4 = 0) (5 = 4)
recode v101 (1 = 2) (2 = 1)
recode v106 (1 = 0) (2 = 1) (3 = 2) (4 = 3) (5 = 4)
recode v_902_roughly_what_was_you (1 = 2) (2 = 5) (3 = 3) (4 = 4) (5 = 1) (6 = .)
recode v114 (1 = 1) (2 = 0)
recode v1001 (1 = 1) (2 = 3) (3 = 4) (4 = 2)
recode v121 (1 = 4) (2 = 2) (3 = 1) (4 = 3)
recode has_any_household_member_1 (1 = 1) (2 = 0)
recode does_your_household_own_a__002 (1 = 1) (2 = 0)
recode how_would_you_rate_the_dig (1 = 0) (2 = 3) (3 = 1) (4 = 2)
recode v113 (1 = 1) (2 = 0)
recode v103 (1 = 5) (2 = 1) (3 = 2) (4 = 3) (5 = 4)
recode v_901_what_is_the_primary_ (1 = 3) (2 = 2) (3 = 1) (4 = 7) (5 = 4) (6 = 6) (7 = 5)

* 3. Complete cases across the outcome, all 15 predictors, and design fields.
drop if missing(what_is_the_main_way_your_)
drop if missing(residence3)
drop if missing(v102)
drop if missing(v101)
drop if missing(v106)
drop if missing(v_902_roughly_what_was_you)
drop if missing(v114)
drop if missing(v1001)
drop if missing(v104)
drop if missing(v121)
drop if missing(has_any_household_member_1)
drop if missing(does_your_household_own_a__002)
drop if missing(how_would_you_rate_the_dig)
drop if missing(v113)
drop if missing(v103)
drop if missing(v_901_what_is_the_primary_)

drop if missing(id, wgt, bahda_strata_code)
drop if wgt <= 0

* 4. Rename every retained variable.
rename what_is_the_main_way_your_ DV_internet_access_mode
rename residence3 residence
rename v102 head_age
rename v101 head_sex
rename v106 head_education
rename v_902_roughly_what_was_you monthly_expenditure
rename v114 smartphone
rename v1001 electricity_source
rename v104 household_size
rename v121 head_employment
rename has_any_household_member_1 youth_vocational_training
rename does_your_household_own_a__002 computer_tablet
rename how_would_you_rate_the_dig head_digital_literacy
rename v113 basic_mobile
rename v103 head_marital_status
rename v_901_what_is_the_primary_ primary_income_source
rename id record_id
rename wgt survey_weight
rename bahda_strata_code sampling_stratum
rename v_002_zone zone
rename v_003_sub_zone sub_zone
label variable zone "Zone"
label variable sub_zone "Sub-zone"
label define lbl_internet_access_mode 0 "No internet access" 1 "Mobile data on smartphone" 2 "Mobile data on feature phone" 3 "Home Wi-Fi/Fiber" 4 "Public Wi-Fi/Cyber Cafe", replace
label values DV_internet_access_mode lbl_internet_access_mode
label define lbl_residence 1 "Urban" 2 "Peri-Urban" 3 "Rural", replace
label values residence lbl_residence
label define lbl_head_sex 1 "Female" 2 "Male", replace
label values head_sex lbl_head_sex
label define lbl_head_education 0 "No schooling" 1 "Primary" 2 "Secondary" 3 "TVET" 4 "University", replace
label values head_education lbl_head_education
label define lbl_monthly_expenditure 1 "Less than 100 USD" 2 "100-299 USD" 3 "300-599 USD" 4 "600-999 USD" 5 "1000 USD or more", replace
label values monthly_expenditure lbl_monthly_expenditure
label define lbl_smartphone 0 "No" 1 "Yes", replace
label values smartphone lbl_smartphone
label define lbl_electricity_source 1 "Electric system / Grid" 2 "Solar" 3 "Generator" 4 "No access", replace
label values electricity_source lbl_electricity_source
label define lbl_head_employment 1 "Self-employed" 2 "Private" 3 "Unemployed" 4 "Government", replace
label values head_employment lbl_head_employment
label define lbl_youth_vocational_training 0 "No" 1 "Yes", replace
label values youth_vocational_training lbl_youth_vocational_training
label define lbl_computer_tablet 0 "No" 1 "Yes", replace
label values computer_tablet lbl_computer_tablet
label define lbl_head_digital_literacy 0 "Cannot use digital devices/internet" 1 "Low" 2 "Moderate" 3 "High", replace
label values head_digital_literacy lbl_head_digital_literacy
label define lbl_basic_mobile 0 "No" 1 "Yes", replace
label values basic_mobile lbl_basic_mobile
label define lbl_head_marital_status 1 "Married" 2 "Polygamous" 3 "Single" 4 "Widowed" 5 "Divorced", replace
label values head_marital_status lbl_head_marital_status
label define lbl_primary_income_source 1 "Informal wage labor" 2 "Formal salary" 3 "Agriculture/livestock" 4 "Own business/self-employment" 5 "Remittances from abroad" 6 "Pensions/social welfare" 7 "Other", replace
label values primary_income_source lbl_primary_income_source

assert !missing(survey_weight) & survey_weight > 0
assert !missing(record_id, sampling_stratum)
isid record_id
assert _N == 2707 // Expected with the supplied source file
compress
save "data/p15_internet_access_modes_clean.dta", replace
