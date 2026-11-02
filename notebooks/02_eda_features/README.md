# Member 2: EDA and shared forecasting features

## Scope

This folder contains Member 2's contribution to the San Jose 311 illegal-dumping project. The project studies reported weekly demand by council district; a request is a 311 report, not necessarily a distinct dumping event. Member 2 verifies the fixed district map, describes the cleaned data, implements leakage-safe shared features, and compares predeclared feature groups with the team's Poisson forecasting convention.

All findings are **provisional** until the team approves the source-coverage and fixed-geography assumptions. This work does not evaluate the reserved 2025 test period.

## Execution order

Run the notebooks from a location inside the repository, in this order:

1. `01_district_map_verification.ipynb` verifies districts 1-10, polygon validity, point assignment, unmatched coordinates, and boundary sensitivity.
2. `02_exploratory_data_analysis.ipynb` describes missingness, reporting time and channel patterns, fixed-district demand, and unusually high reporting weeks.
3. `03_feature_engineering.ipynb` reconstructs the shared district-week panel and verifies the reusable calendar, lag, and rolling features in `../../src/eda_features.py`.
4. `04_feature_comparison.ipynb` holds the model and rows fixed while comparing three feature groups through `../../src/feature_comparison.py`.

The notebooks locate the repository root at runtime and use repository-relative paths. They do not depend on a user's home-directory path.

## Environment

The repository's pinned dependencies are in `requirements-forecasting.txt`. From the repository root:

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements-forecasting.txt
.venv/bin/python -m unittest discover -s tests -v
```

The saved notebooks were most recently reproduced with Python 3.11.15 and the pinned package versions: NumPy 1.26.4, pandas 2.3.3, scikit-learn 1.6.1, Shapely 2.0.7, and Matplotlib 3.9.4. The requirements-file header still says Python 3.9.6; team confirmation is needed before changing that shared file. The notebooks can be run with the `.venv` kernel in VS Code. Command-line execution also requires a notebook runner such as `nbconvert`; that package is present in the reviewed environment but is not explicitly pinned in the shared requirements file.

## Inputs and data identity

The workflow uses only existing local project inputs:

| Input | Purpose | SHA-256 |
| --- | --- | --- |
| `data/processed/illegal_dumping_cleaned.csv` | Cleaned request-level handoff | `c075709e37fa3050f5d53c94fb9db486e169c44a13d2fdee9fa735d3ef2a7e8c` |
| `data/reference/council_districts_snapshot.geojson` | Frozen council-district polygons | `29ba080e546a747541716349e4c0620923a751322ea37a153646f4005ea31430` |
| `data/reference/council_districts_metadata.json` | ArcGIS layer metadata | `ef185ae51b0e2128f5c1fa24c679ff63f42b2b84f4c220114ac2adab6ef4fb0a` |
| `results/demand_forecasting/location_audit.csv` | Teammate location-audit comparison | `4a793264f1628c54de4061faa7a2d18ad57b018ef89f5c536261ad27ee141272` |

The cleaned data and reference files are currently tracked, so they are available in a fresh checkout at these paths. The notebooks stop with an explicit error if a required input is absent or incompatible.

## Verified map and EDA findings

The saved map contains exactly districts 1-10. All ten geometries are non-empty, valid polygons or multipolygons. Among 181,326 cleaned requests dated 2018-2024, 180,863 map uniquely, 463 are unmatched, and none matches multiple districts. Unmatched points are preserved for investigation rather than corrected or deleted.

Important descriptive findings include:

- Original `category` is missing for 97.7% of all cleaned rows, while request ID, creation time, latitude, and longitude are complete.
- Development-period volume rose from 22,709 reports in 2018 to 29,909 in 2024; this is descriptive and does not establish a causal demand increase.
- Tuesday is the most common creation weekday, and Public API is the most common exact reporting channel.
- District 3 has the largest raw mapped total, 38,654 reports or 21.37% of mapped development reports. Counts are not population-adjusted.
- Ten complete 2018-2024 weeks exceed the declared `Q3 + 1.5 * IQR` reporting-volume screen. These are flags for investigation, not confirmed events.

The EDA notebook reads 2025 only to label and separate the reserved records during inventory and missingness checks. All forecasting-oriented EDA, anomaly thresholds, panel construction, feature comparisons, and model metrics use 2018-2024 only. No 2025 model evaluation is performed.

## Feature methodology

The target is the number of uniquely mapped reports created in one district during a complete Monday-Sunday week. The in-memory panel contains 3,650 rows: ten districts by 365 complete week starts from 2018-01-01 through 2024-12-23. Its target sums to 180,732 reports. Another 131 uniquely mapped reports belong to the week starting 2024-12-30, which crosses into the reserved test year and is excluded from development scoring.

Calendar features are known at the beginning of the forecast week:

- `month`: calendar month of `week_start`.
- `week_of_year`: ISO week number.
- `sin_year`, `cos_year`: cyclic annual position using `2 * pi * day_of_year / 365.25`.

Historical-demand features are calculated separately within each district on a continuous weekly grid:

- `lag_1`, `lag_2`, `lag_4`, `lag_8`: counts from completed earlier weeks.
- `rolling_4`, `rolling_8`, `rolling_13`: shifted means over completed earlier weeks.
- `rolling_std_4`, `rolling_std_8`: shifted sample standard deviations (`ddof=1`).
- `recent_change_1_4`: `lag_1 - rolling_4`.

Every rolling calculation shifts by one week before aggregation, so a week's target cannot enter its own predictors. The complete field-level specification is in `feature_dictionary.csv`. Seven overlapping definitions are also checked against `src/demand_forecasting.py` without modifying that teammate module.

## Development split and model convention

- Feature history: 2018-2019, used only to supply past observations.
- Training: 2,080 district-weeks from complete weeks in 2020-2023.
- Validation: 520 district-weeks, ten districts by 52 complete weeks from 2024-01-01 through 2024-12-23.
- Reserved test: 2025, not evaluated.
- Excluded edge: the week beginning 2024-12-30 because its Monday-Sunday interval crosses into 2025.

All ablation experiments use identical keys and targets. District is one-hot encoded, numeric inputs are standardized, and preprocessing is fitted on training rows only. Every group uses `PoissonRegressor(alpha=1, max_iter=2000, tol=1e-8)` with no hyperparameter tuning.

## Provisional 2024 feature comparison

| Group | Features | MAE | RMSE |
| --- | --- | ---: | ---: |
| A: basic | district and four calendar features | 17.861 | 24.532 |
| B: basic + lags | A plus lags 1, 2, 4, and 8 | **13.852** | **19.482** |
| C: basic + lags + rolling | B plus six rolling/change features | 14.131 | 19.781 |

Group B has the lowest predeclared 2024 validation MAE and RMSE. Relative to A, it reduces MAE by 22.45% and RMSE by 20.58%. Adding the full rolling group does not improve on B in this validation experiment.

The existing teammate 2020-start Poisson result is MAE 13.643 and RMSE 19.132. It uses the same validation keys and targets but a different feature combination, so it is reported as context rather than as one of Member 2's A/B/C groups. Validation improvement does not guarantee performance on the untouched 2025 test period.

Reproducible outputs are stored in:

- `../../results/member2/feature_comparison_metrics.csv`
- `../../results/member2/feature_comparison_predictions.csv`
- `../../reports/figures/member2/feature_comparison.png`

## Limitations and open decisions

- The frozen layer is described as current/2021-redistricting geography with possible later updates. Applying it to 2018-2024 is consistent retrospective geography, not proof of the district legally in effect for every historical request.
- The GeoJSON coordinate ranges support longitude/latitude use, but the export query, acquisition timestamp, and requested output CRS are not recorded.
- The team still needs to approve fixed geography and decide whether historical-boundary sensitivity analysis is required.
- Annual export completeness and the interpretation of an unobserved district-week as zero demand require confirmation. The current reconstructed grid happened to have zero unobserved district-week cells.
- Request counts measure reports and can change with channel access, source systems, public behavior, and definitions.
- Raw district comparisons do not adjust for population, area, land use, or reporting access.
- Poisson regression models the conditional mean and does not provide calibrated prediction intervals here; counts may be overdispersed or temporally correlated.

## Reproduction checks

After running the notebooks in order, run:

```sh
.venv/bin/python -m unittest discover -s tests -v
git status --short
git diff --check
```

Expected evidence includes 25 passing tests, executed notebooks with no error outputs, exact map-audit reconciliation, identical A/B/C training and validation keys, identical validation targets, finite non-negative predictions, and unchanged teammate forecasting-file hashes.

## Individual contribution summary

Member 2 contributed the district-map audit and limitations record, interpreted EDA, reusable leakage-safe feature functions, a field-level feature dictionary, a controlled Poisson feature-ablation experiment, saved metrics/predictions/figure, and tests for time ordering, row compatibility, preprocessing isolation, finite outputs, and preservation of teammate files. Teammate data cleaning and forecasting implementations were reused as read-only dependencies and were not changed by this contribution.
