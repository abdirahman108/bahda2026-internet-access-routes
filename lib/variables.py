"""Variable definitions, data loading and model design matrices."""
from pathlib import Path
import numpy as np
import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "borama_internet_access.dta"
OUT = ROOT / "outputs"

OUTCOME = "DV_internet_access_mode"
OUT_LABELS = {0: "No internet access", 1: "Mobile data on smartphone", 2: "Mobile data on feature phone",
              3: "Home Wi-Fi/fibre", 4: "Public Wi-Fi/cyber café"}
OUT_SHORT = {0: "No access", 1: "Smartphone data", 2: "Feature-phone data", 3: "Home Wi-Fi/fibre",
             4: "Public Wi-Fi/café"}

# name, label, type, reference level, ordered level codes
CATS = [
    ("residence", "Residence", 1, [1, 2, 3]),
    ("head_sex", "Sex of household head", 2, [2, 1]),
    ("head_education", "Education of household head", 0, [0, 1, 2, 3, 4]),
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

# Ten predictors selected a priori for their relevance to household internet access,
# entered in three blocks for the sequential models (manuscript Section 2.10)
BLOCK_A = ["residence", "head_age", "head_sex", "head_education", "household_size"]
BLOCK_B = ["head_employment", "monthly_expenditure", "electricity_source", "youth_vocational_training"]
BLOCK_C = ["smartphone"]
PRIMARY = BLOCK_A + BLOCK_B + BLOCK_C
SELECTED10 = ["residence", "head_age", "head_sex", "head_education", "monthly_expenditure", "smartphone",
           "electricity_source", "household_size", "head_employment", "youth_vocational_training"]
assert sorted(PRIMARY) == sorted(SELECTED10)
# further household ICT items kept in the cleaned file, used only in a sensitivity model
EXTRA = ["head_marital_status", "primary_income_source", "basic_mobile", "computer_tablet",
         "head_digital_literacy"]


def load():
    df, meta = pyreadstat.read_dta(str(DATA))
    vl = {k: meta.value_labels.get(v, {}) for k, v in meta.variable_to_label.items()}
    for c in df.columns:
        if c not in ("sub_zone",) and df[c].dtype != object:
            pass
    df["psu_hh"] = df["record_id"].astype("int64").astype(str)
    # Sensitivity PSU: operational sub-zone cluster in the four urban strata; each household
    # is its own PSU where no complete cluster code exists (peri-urban, rural, and a few urban records).
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
