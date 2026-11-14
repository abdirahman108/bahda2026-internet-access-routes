"""Variable names, codes, and comparison groups; loading the data; and building the model inputs."""
from pathlib import Path
import os

import numpy as np
import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]
# The data file. To keep the file where it is, set the BAHDA_DATA environment variable to its full path.
DATA = Path(os.environ.get("BAHDA_DATA", ROOT / "data" / "borama_internet_access.dta"))
OUT = ROOT / "outputs"

OUTCOME = "DV_internet_access_mode"
OUT_LABELS = {0: "No internet access", 1: "Mobile data on smartphone", 2: "Mobile data on feature phone",
              3: "Home Wi-Fi/fibre", 4: "Public Wi-Fi/cyber café"}
OUT_SHORT = {0: "No access", 1: "Smartphone data", 2: "Feature-phone data", 3: "Home Wi-Fi/fibre",
             4: "Public Wi-Fi/café"}

# For each categorical variable: name, label, reference (comparison) code, and the codes in display order
CATS = [
    ("residence", "Residence", 1, [1, 2, 3]),
    ("head_sex", "Sex of household head", 2, [2, 1]),
    ("head_education", "Education of household head", 1, [1, 2, 3, 4, 0]),
    ("head_marital_status", "Marital status of household head", 1, [1, 2, 3, 4, 5]),
    ("head_employment", "Employment status of household head", 1, [1, 2, 3, 4]),
    ("primary_income_source", "Primary household income source", 1, [1, 2, 3, 4, 5, 6, 7]),
    ("monthly_expenditure", "Average monthly household expenditure", 1, [1, 2, 3, 4, 5]),
    ("electricity_source", "Primary electricity source", 1, [1, 2, 3, 4]),
    ("smartphone", "Household owns a smartphone", 0, [0, 1]),
    ("basic_mobile", "Household owns a functional basic mobile phone", 0, [0, 1]),
    ("computer_tablet", "Household owns a computer or tablet", 0, [0, 1]),
    ("head_digital_literacy", "Digital literacy of household head", 0, [0, 1, 2, 3]),
    ("youth_vocational_training", "Member aged 15–35 completed vocational/technical training", 0, [0, 1]),
]
CONTS = [("head_age", "Age of household head (years)", 10.0),
         ("household_size", "Household size (members)", 1.0)]

# The ten predictors, chosen before the analysis began. Models 1 to 3 add them in three groups
# (manuscript Section 2.10).
BLOCK_A = ["residence", "head_age", "head_sex", "head_education", "household_size"]
BLOCK_B = ["head_employment", "monthly_expenditure", "electricity_source", "youth_vocational_training"]
BLOCK_C = ["smartphone"]
PRIMARY = BLOCK_A + BLOCK_B + BLOCK_C
SELECTED10 = ["residence", "head_age", "head_sex", "head_education", "monthly_expenditure", "smartphone",
           "electricity_source", "household_size", "head_employment", "youth_vocational_training"]
assert sorted(PRIMARY) == sorted(SELECTED10)
# Five extra questions about household technology, used only in sensitivity analysis S5
EXTRA = ["head_marital_status", "primary_income_source", "basic_mobile", "computer_tablet",
         "head_digital_literacy"]


def load():
    df, meta = pyreadstat.read_dta(str(DATA))
    vl = {k: meta.value_labels.get(v, {}) for k, v in meta.variable_to_label.items()}
    # Education code 0 means the answer is missing, according to the BAHDA variable guide and Atlas
    # Table 1.1.8. It stays as its own "Not reported" group, so no household is left out. Older versions
    # of the analysis file label this code "No schooling".
    vl.setdefault("head_education", {})[0] = "Not reported"
    for c in df.columns:
        if c not in ("sub_zone",) and df[c].dtype != object:
            pass
    df["psu_hh"] = df["record_id"].astype("int64").astype(str)
    # Sampling units for sensitivity analysis S1: the sub-zone in the four urban strata. Where there is no
    # sub-zone code (peri-urban, rural, and a few urban households), each household is its own unit.
    urban_cluster = (df["sampling_stratum"] <= 4) & (df["sub_zone"].str.strip() != "")
    df["psu_cluster"] = np.where(urban_cluster, "C_" + df["sub_zone"].astype(str), "H_" + df["psu_hh"])
    return df, vl


def term_name(var, lv):
    return f"{var}={int(lv)}"


def design(df, preds, age_scale=True):
    cols = {}
    for name, label, ref, levels in CATS:
        if name not in preds:
            continue
        for lv in levels:
            if lv == ref:
                continue
            cols[term_name(name, lv)] = (df[name] == lv).astype(float)
    for name, label, scale in CONTS:
        if name not in preds:
            continue
        cols[name] = df[name].astype(float) / (scale if age_scale else 1.0)
    return pd.DataFrame(cols, index=df.index)
