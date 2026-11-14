# Independent cross-check of the main model (Model 3) in R.
#
# The published estimates come from the Python code in this repository (lib/svy.py). This script fits
# the same survey-weighted multinomial logistic regression with the R packages survey and svyVGAM,
# which were written independently, and saves the coefficients and standard errors so that
# 7_compare_r.py can put the two sets of results side by side.
#
# Design, as in the manuscript: stratum weights, six strata, each household as its own sampling unit,
# Taylor-series linearised variances.
#
# To run this script, from the repository's main folder, run:
#     Rscript scripts/r_crosscheck.R
# It reads data/borama_internet_access.dta, or the file named in the BAHDA_DATA environment variable.
suppressPackageStartupMessages({
  library(haven)
  library(survey)
  library(VGAM)
  library(svyVGAM)
})

path <- Sys.getenv("BAHDA_DATA", unset = file.path("data", "borama_internet_access.dta"))
d <- as.data.frame(zap_labels(read_dta(path)))
stopifnot(nrow(d) == 2707)

# The same comparison groups as the Python code (lib/variables.py)
d$y <- factor(d$DV_internet_access_mode, levels = 0:4)
d$residence <- relevel(factor(d$residence), ref = "1")
d$head_sex <- relevel(factor(d$head_sex), ref = "2")
d$head_education <- relevel(factor(d$head_education), ref = "1")
d$head_employment <- relevel(factor(d$head_employment), ref = "1")
d$monthly_expenditure <- relevel(factor(d$monthly_expenditure), ref = "1")
d$electricity_source <- relevel(factor(d$electricity_source), ref = "1")
d$smartphone <- relevel(factor(d$smartphone), ref = "0")
d$youth_vocational_training <- relevel(factor(d$youth_vocational_training), ref = "0")
d$head_age10 <- d$head_age / 10

des <- svydesign(ids = ~record_id, strata = ~sampling_stratum, weights = ~survey_weight, data = d)

fit <- svy_vglm(
  y ~ residence + head_age10 + head_sex + head_education + household_size + head_employment +
    monthly_expenditure + electricity_source + youth_vocational_training + smartphone,
  family = multinomial(refLevel = 1), design = des
)

b <- coef(fit)
se <- sqrt(diag(vcov(fit)))
# VGAM names each coefficient "<term>:<k>", where k = 1..4 is the k-th route after the reference
# (1 = smartphone data, 2 = feature-phone data, 3 = home Wi-Fi/fibre, 4 = public Wi-Fi/cyber cafe)
nm <- names(b)
out <- data.frame(
  outcome = as.integer(sub(".*:", "", nm)),
  r_term = sub(":[0-9]+$", "", nm),
  b_r = unname(b), se_r = unname(se)
)
dir.create(file.path("outputs", "tables"), recursive = TRUE, showWarnings = FALSE)
write.csv(out, file.path("outputs", "tables", "r_crosscheck_coefficients.csv"), row.names = FALSE)

# Weighted share of each route with a 95% CI, for the descriptive comparison
p <- svymean(~y, des)
write.csv(data.frame(level = 0:4, p_r = unname(coef(p)), se_r = unname(SE(p))),
          file.path("outputs", "tables", "r_crosscheck_outcome.csv"), row.names = FALSE)

ver <- c(R = R.version.string,
         survey = as.character(packageVersion("survey")),
         svyVGAM = as.character(packageVersion("svyVGAM")),
         VGAM = as.character(packageVersion("VGAM")),
         haven = as.character(packageVersion("haven")))
writeLines(paste(names(ver), ver, sep = ": "), file.path("outputs", "r_versions.txt"))
cat("R cross-check written:", nrow(out), "coefficients\n")
