"""Totals for all 2,896 households, copied from the BAHDA-2026 Atlas.

The analysis file contains only the 2,707 households with complete answers. These published totals
are used in two places:

- 4_excluded_households.py subtracts the analysis file's counts from them to describe the 189
  households that were left out.
- Sensitivity analysis S12 adjusts the survey weights to match them.
"""
from variables import OUTCOME

# Atlas Table 2.15: households that took part, by stratum (stratum codes as in the analysis file)
ATLAS_STRATUM = {1: 602, 2: 615, 3: 627, 4: 616, 5: 217, 6: 219}

# Atlas tables for all 2,896 households: {code in the analysis file: (count, weighted count)}
ATLAS = {
    (OUTCOME, "4.1.6"): {0: (312, 653.4), 1: (853, 961.3), 2: (630, 601.5), 3: (1010, 622.7), 4: (91, 57.0)},
    ("head_sex", "1.1.4"): {1: (1512, 1462.8), 2: (1384, 1433.2)},
    ("head_education", "1.1.8"): {0: (615, 847.2), 1: (640, 712.4), 2: (473, 464.0), 3: (84, 96.8),
                                  4: (1084, 775.6)},
    ("head_employment", "1.4.1"): {1: (1169, 1259.8), 2: (815, 641.3), 3: (432, 595.5), 4: (480, 399.3)},
    ("electricity_source", "4.4.1"): {1: (2139, 1647.3), 2: (418, 669.2), 3: (150, 178.6), 4: (189, 400.9)},
    ("smartphone", "4.1.2"): {0: (448, 653.5), 1: (2448, 2242.5)},
    ("youth_vocational_training", "1.3.1"): {0: (1332, 1624.0), 1: (1564, 1272.0)},
}
# Atlas Tables 1.1.5 and 1.1.7: averages for all 2,896 households (without weights, with weights)
ATLAS_MEANS = {"head_age": (43.956, 44.236), "household_size": (8.121, 8.021)}
N_FULL, N_EXC = 2896, 189


def calibrated_weights(data, margins=("sampling_stratum", OUTCOME, "head_employment", "electricity_source"),
                       iters=200):
    """Adjust the survey weights so that the 2,707 households match the Atlas totals for all 2,896.

    The method is raking: it adjusts the weights for one variable at a time and repeats until all of
    them match. The targets are the Atlas weighted counts. For each stratum, the target is the number of
    households that took part times the stratum weight. The adjusted weights stand in for the left-out
    households on these variables.
    """
    w = data["survey_weight"].to_numpy(dtype=float).copy()
    ws = data.groupby("sampling_stratum")["survey_weight"].first()
    targets = {"sampling_stratum": {s: ATLAS_STRATUM[s] * ws[s] for s in ATLAS_STRATUM}}
    for (var, _), counts in ATLAS.items():
        if var in margins:
            targets[var] = {k: v[1] for k, v in counts.items()}
    for _ in range(iters):
        for var in margins:
            x = data[var].to_numpy()
            for k, t in targets[var].items():
                m = x == k
                w[m] *= t / w[m].sum()
    return w * len(w) / w.sum()
