


# San José 311 Illegal-Dumping Demand Forecasting

A reproducible machine-learning project for analyzing and forecasting weekly San José 311 illegal-dumping report demand across City Council districts.

The project covers the complete workflow from data collection and cleaning through exploratory analysis, spatial verification, feature engineering, baseline modeling, Poisson regression, Random Forest, and XGBoost experiments.

> **Important:** This project predicts the number of 311 reports received, not the true number of illegal-dumping incidents. Results are provisional because source completeness, timestamp interpretation, zero-filled weeks, and historical district-boundary assumptions still require final team confirmation.

---

## Table of Contents

- [Project Objective](#project-objective)
- [Problem Definition](#problem-definition)
- [Why Demand Forecasting Was Selected](#why-demand-forecasting-was-selected)
- [Data Sources](#data-sources)
- [Project Workflow](#project-workflow)
- [Data Preparation Summary](#data-preparation-summary)
- [Geographic Assignment](#geographic-assignment)
- [Forecasting Protocol](#forecasting-protocol)
- [Feature Engineering](#feature-engineering)
- [Models and Results](#models-and-results)
- [Team Contributions](#team-contributions)
- [Repository Structure](#repository-structure)
- [Installation](#installation)
- [Reproduction Instructions](#reproduction-instructions)
- [Testing](#testing)
- [Generated Outputs](#generated-outputs)
- [Limitations](#limitations)
- [Current Project Status](#current-project-status)
- [Collaboration](#collaboration)

---

## Project Objective

The objective is to determine whether historical San José 311 reporting patterns can forecast weekly illegal-dumping report demand for each City Council district.

Each forecasting observation represents:

```text
One Council district × one complete Monday–Sunday week
```

The prediction target is:

```text
Number of newly created illegal-dumping 311 reports during that week
```

Potential operational uses include:

- Anticipating relative service demand.
- Comparing expected workload across districts.
- Identifying weeks that may require additional operational capacity.
- Supporting data-informed planning.

The project does not:

- Predict individual illegal-dumping events.
- Identify offenders.
- Measure every real illegal-dumping incident.
- Establish causal relationships.
- Automatically assign public resources.

---

## Problem Definition

This is a supervised count-regression and time-based forecasting problem.

The models use information that would be available before the forecasted week, including:

- Council district.
- Calendar position.
- Counts from previously completed weeks.
- Shifted historical averages.
- Shifted historical variation.

Model performance is measured using:

- Mean Absolute Error (MAE)
- Root Mean Squared Error (RMSE)

Both metrics are expressed in reports per district-week. Lower values indicate better predictive performance.

---

## Why Demand Forecasting Was Selected

The original project plan considered three possible tasks:

1. Slow-resolution classification.
2. Resolution-time regression.
3. Weekly report-demand forecasting.

The source data includes `Date Last Updated`, but the repository has not established that this field represents the true completion time of a service request.

Using it as a case-closure timestamp could create unreliable classification labels and inaccurate resolution durations. Therefore, closure-based classification and resolution-time regression were not selected as the primary tasks.

The team adopted weekly illegal-dumping report-demand forecasting as the shared modeling problem.

The directory names below remain from the original project structure:

```text
notebooks/03_classification/
notebooks/04_resolution_regression/
```

However:

- `03_classification` currently contains Random Forest demand regression.
- `04_resolution_regression` contains XGBoost demand regression on Member 4’s branch.

---

## Data Sources

### San José 311 service requests

Official source:

[City of San José 311 Service Request Data](https://data.sanjoseca.gov/dataset/311-service-request-data)

The data-preparation pipeline uses the City of San José CKAN API to identify and download annual CSV resources.

The committed cleaned dataset covers:

```text
2018–2025
```

### San José Council district boundaries

Official source:

[City of San José Council District ArcGIS Layer](https://geo.sanjoseca.gov/server/rest/services/PLN/PLN_AdministrativeBoundaries/MapServer/1)

The repository contains a frozen district-boundary snapshot and metadata:

```text
data/reference/council_districts_snapshot.geojson
data/reference/council_districts_metadata.json
```

The snapshot contains Council Districts 1–10.

The layer represents current/2021-redistricting geography and may include later updates. Applying this single snapshot to all historical records creates consistent retrospective geography, but it does not reconstruct the legally applicable district boundaries for every historical year.

---

## Project Workflow

```text
Annual San José 311 CSV files
             |
             v
Cross-year schema standardization
             |
             v
Illegal-dumping report identification
             |
             v
Request ID, timestamp, coordinate, and duplicate checks
             |
             v
Cleaned request-level dataset
             |
             v
Council-district spatial assignment
             |
             v
Continuous district-week panel
             |
             v
Calendar, lag, and rolling-history features
             |
             v
Training on 2020–2023
             |
             v
Development validation on 2024
             |
             v
Reserved final test on 2025
```

The 2025 final test period has not been evaluated.

---

## Data Preparation Summary

The committed cleaning run processed eight annual files covering 2018–2025.

| Cleaning stage | Records |
|---|---:|
| Source rows across all years | 2,002,143 |
| Illegal-dumping rows before quality rules | 214,502 |
| Excluded for quality issues | 1,071 |
| Exact duplicate rows removed | 0 |
| Repeated request IDs removed | 0 |
| Final retained records | 213,431 |

### Cleaning rules

The data-preparation pipeline:

- Maps changing annual column names to a common schema.
- Searches `Service Type` and `Category` for illegal-dumping labels.
- Matches `Illegal Dumping` and `Illegal Dump` case-insensitively.
- Excludes records without a usable request ID.
- Excludes records without a valid creation timestamp.
- Excludes implausible coordinates when coordinates are present.
- Removes exact duplicate rows.
- Removes repeated request IDs while keeping the first chronological record.
- Preserves original category and source fields for auditing.
- Standardizes the final service label to `Illegal Dumping`.
- Retains `Date Last Updated` without treating it as a completion timestamp.

### Cleaned schema

The cleaned dataset includes:

| Field | Description |
|---|---|
| `request_id` | Unique 311 service-request identifier |
| `status` | Status reported by the source |
| `source` | Request submission channel |
| `category` | Original source category |
| `service_type` | Standardized illegal-dumping label |
| `latitude` | Request latitude |
| `longitude` | Request longitude |
| `date_created` | Parsed creation timestamp |
| `date_last_updated` | Source update timestamp |
| `department` | Responsible source department |
| `source_year` | Annual source-file year |

---

## Geographic Assignment

The forecasting pipeline assigns requests to Council Districts 1–10 using the frozen GeoJSON boundary snapshot.

For the 2018–2024 development period:

| Geographic check | Records |
|---|---:|
| Cleaned requests | 181,326 |
| Uniquely assigned to a district | 180,863 |
| Outside all saved district polygons | 463 |
| Matching multiple districts | 0 |

Unmatched records are preserved for investigation. They are not deleted, corrected, or automatically forced into the nearest district.

Possible explanations include:

- Coordinates outside the city boundary.
- Coordinate imprecision.
- Boundary-version differences.
- Annexation or city-limit changes.
- Source coordinate problems.
- Retrospective use of one current district map.

The full verification is documented in:

```text
notebooks/02_eda_features/district_map_verification.md
```

---

## Forecasting Protocol

### Time periods

| Purpose | Period |
|---|---|
| Historical feature support | 2018–2019 |
| Model training | 2020–2023 |
| Development validation | 2024 |
| Reserved final test | 2025 |

The 2024 validation set contains:

- 52 complete weeks.
- 10 Council districts.
- 520 district-week rows.

The latest included validation week begins on December 23, 2024.

The week beginning December 30, 2024 is excluded because it crosses into the reserved 2025 test period.

### Forecast interpretation

At the beginning of a forecast week, the model predicts that week’s report count using already completed earlier weeks.

The evaluation is rolling one-week-ahead validation:

- Models are fitted using 2020–2023 training rows.
- The fitted model remains fixed throughout 2024.
- Actual counts from completed earlier weeks may supply lag history.
- The current week’s count cannot enter its own predictors.
- Future weeks cannot modify earlier feature values.
- Preprocessing is fitted using training rows only.
- All districts from a given week remain in the same chronological split.

This is not equivalent to forecasting all of 2024 at once using only information available on January 1, 2024.

---

## Feature Engineering

### District feature

- Council district identity.
- One-hot encoded for Poisson regression.
- One-hot encoded before Random Forest and XGBoost modeling.

### Calendar features

- `month`
- `week_of_year`
- `sin_year`
- `cos_year`

The sine and cosine features represent the annual calendar cycle without treating December and January as far apart.

### Lag features

- `lag_1`: count from one completed week earlier.
- `lag_2`: count from two completed weeks earlier.
- `lag_4`: count from four completed weeks earlier.
- `lag_8`: count from eight completed weeks earlier.

### Rolling-history features

- `rolling_4`: shifted 4-week mean.
- `rolling_8`: shifted 8-week mean.
- `rolling_13`: shifted 13-week mean.
- `rolling_std_4`: shifted 4-week standard deviation.
- `rolling_std_8`: shifted 8-week standard deviation.
- `recent_change_1_4`: previous-week count minus shifted 4-week mean.

All rolling calculations are shifted by one week before aggregation. Therefore, the current target cannot enter its own feature values.

The full feature dictionary is available at:

```text
notebooks/02_eda_features/feature_dictionary.csv
```

---

## Models and Results

All results below are provisional 2024 development-validation results.

The 2025 final test set remains untouched.

### Shared baselines and Poisson regression

| Model | Training period | MAE | RMSE |
|---|---|---:|---:|
| Previous-week baseline | Not applicable | 15.804 | 22.271 |
| Four-week-average baseline | Not applicable | 15.030 | 20.714 |
| Poisson regression | 2018–2023 | 13.843 | 19.415 |
| **Poisson regression** | **2020–2023** | **13.643** | **19.132** |

The Poisson model trained on 2020–2023 is the strongest result currently merged into `main`.

It reduces MAE by approximately 9.23% relative to the four-week-average baseline.

### Member 2 Poisson feature comparison

| Feature group | MAE | RMSE |
|---|---:|---:|
| District and calendar features | 17.861 | 24.532 |
| **District, calendar, and lag features** | **13.852** | **19.482** |
| District, calendar, lag, and rolling features | 14.131 | 19.781 |

Adding lag features reduced MAE by approximately 22.45% relative to the basic feature group.

Adding the complete rolling-feature group did not improve performance beyond the lag-based group in this experiment.

### Member 3 Random Forest comparison

| Random Forest experiment | MAE | RMSE |
|---|---:|---:|
| **Without rolling features** | **14.027** | **20.107** |
| Full model | 14.090 | 20.413 |
| Without calendar features | 14.221 | 20.626 |
| Without lag features | 14.917 | 22.017 |
| Basic calendar model | 18.675 | 27.101 |

The strongest Random Forest configuration keeps:

- District identity.
- Calendar cycle.
- Lag 1.
- Lag 2.
- Lag 4.

It excludes rolling-average features.

The increase in error after removing lag features indicates that recent report history is important for Random Forest forecasting.

### Member 4 XGBoost comparison

Member 4’s XGBoost work is available on:

```text
origin/Xinghan/xgboost-demand-forecasting
```

It is not merged into the current `main` branch.

| XGBoost feature configuration | MAE | RMSE |
|---|---:|---:|
| Shared forecasting features | 14.171 | 20.325 |
| **Member 2 calendar and lag features** | **13.942** | **20.195** |
| Member 2 complete feature set | 14.007 | 20.356 |

The calendar-and-lag feature configuration is the strongest XGBoost experiment.

Additional findings include:

- XGBoost improves over the previous-week baseline.
- XGBoost improves over the four-week-average baseline.
- XGBoost does not outperform the 2020–2023 Poisson model.
- District 3 has the largest XGBoost validation error.
- The model tends to underpredict observed high-demand weeks.
- Busy-week analysis is post-hoc error analysis, not an advance busy-week classifier.
- Feature importance values should not be interpreted as causal effects.

### Overall model comparison

| Model/configuration | MAE | RMSE | Status |
|---|---:|---:|---|
| **Poisson, trained 2020–2023** | **13.643** | **19.132** | Merged |
| Poisson with Member 2 lag features | 13.852 | 19.482 | Merged |
| XGBoost with Member 2 lag features | 13.942 | 20.195 | Member 4 branch |
| Random Forest without rolling features | 14.027 | 20.107 | Merged |
| Four-week-average baseline | 15.030 | 20.714 | Merged |
| Previous-week baseline | 15.804 | 22.271 | Merged |

Validation differences should not be treated as final test conclusions. The modeling protocol must be frozen before evaluating 2025.

---

## Team Contributions

Contribution information is based on Git authorship, pull-request history, committed files, notebooks, tests, saved result artifacts, and available remote branches.

Commit counts alone are not used as the measure of contribution.

### Member 1 — Abhijith Reddy: Data Preparation and Cleaning

Merged through pull request #1.

Contributions:

- Developed the reproducible CKAN download pipeline.
- Standardized schemas across annual source files.
- Identified illegal-dumping records.
- Implemented request-ID, date, coordinate, and duplicate checks.
- Created the cleaned request-level dataset.
- Created the source manifest and audit information.
- Produced cleaning counts and a data dictionary.
- Documented the data-preparation workflow and decisions.

Primary files:

```text
src/data_preparation.py
notebooks/01_data_preparation/README.md
data/processed/illegal_dumping_cleaned.csv
data/processed/source_manifest.csv
data/processed/cleaning_counts.csv
data/processed/data_dictionary.csv
results/member1_cleaning_summary.csv
```

Main results:

- Processed 2,002,143 source rows.
- Identified 214,502 illegal-dumping rows before quality rules.
- Excluded 1,071 records for quality problems.
- Retained 213,431 cleaned records.

---

### Member 2 — Haritha Gottumukkala: EDA, District Verification, and Feature Engineering

Merged through pull request #3.

Contributions:

- Verified Council Districts 1–10.
- Checked geometry validity and district identifiers.
- Reproduced request-to-district spatial assignments.
- Investigated unmatched and boundary-sensitive coordinates.
- Reconciled results with the shared location audit.
- Performed exploratory data analysis.
- Examined missingness, annual demand, weekdays, reporting channels, districts, and high-volume weeks.
- Developed leakage-safe calendar, lag, rolling, variation, and recent-change features.
- Created the feature dictionary.
- Conducted a controlled Poisson feature comparison.
- Added feature-engineering and experiment tests.
- Generated validation metrics, predictions, and a comparison figure.

Primary files:

```text
notebooks/02_eda_features/
src/eda_features.py
src/feature_comparison.py
tests/test_eda_features.py
tests/test_feature_comparison.py
results/member2/
reports/figures/member2/
```

Main result:

- The district, calendar, and lag Poisson model achieved MAE 13.852 and RMSE 19.482.

---

### Member 3 — Divija Puli: Random Forest Demand Forecasting

Merged through pull request #4.

Contributions:

- Developed a Random Forest district-week demand model.
- Reused the shared district-week panel.
- Followed the common 2020–2023 training and 2024 validation protocol.
- Conducted five feature-removal experiments.
- Kept eligible rows consistent across experiments.
- Used a fixed random seed for reproducibility.
- Generated validation metrics and row-level predictions.
- Created the feature-removal comparison figure.

Primary files:

```text
notebooks/03_classification/random_forest_forecasting.py
results/member3_random_forest/random_forest_feature_removal_metrics.csv
results/member3_random_forest/random_forest_validation_predictions.csv
reports/figures/member3_random_forest/random_forest_feature_removal.png
```

Main result:

- The best Random Forest model excluded rolling features.
- It achieved MAE 14.027 and RMSE 20.107.

The directory retains the original `classification` name, but the implemented task is Random Forest count regression.

---

### Member 4 — Xinghan Chen (`xinghanchen-xc`): XGBoost Forecasting and Error Analysis

Member 4’s contribution is available on:

```text
origin/Xinghan/xgboost-demand-forecasting
```

The work is completed on the remote branch but is not merged into the current `main` branch.

Contributions:

- Developed XGBoost weekly-demand regression.
- Reused Member 5’s shared district-week panel.
- Reused Member 2’s extended feature functions.
- Compared three XGBoost feature configurations.
- Performed per-district error analysis.
- Performed high-demand or busy-week error analysis.
- Calculated signed prediction bias.
- Generated feature-importance results.
- Created an executed analysis notebook.
- Created five result figures.
- Added seventeen Member 4 tests.
- Created a separately pinned XGBoost environment.
- Added a run manifest containing data hashes, parameters, versions, and assumptions.

Primary branch files:

```text
notebooks/04_resolution_regression/README.md
notebooks/04_resolution_regression/member4_xgboost.py
notebooks/04_resolution_regression/member4_xgboost_analysis.ipynb
notebooks/04_resolution_regression/test_member4_xgboost.py
notebooks/04_resolution_regression/requirements_member4.txt
results/member4_xgboost/
reports/figures/member4_xgboost/
```

Main result:

- The calendar-and-lag XGBoost model achieved MAE 13.942 and RMSE 20.195.
- It improved over the simple baselines but did not outperform Member 5’s Poisson model.

The directory retains the original `resolution_regression` name, but the implemented fallback task is XGBoost weekly-demand forecasting.

---

### Member 5 — Srinidhi Jaya Revanth Srirangarajapally: Shared Forecasting and Project Integration

Member 5 established the repository, developed the shared forecasting pipeline, and integrated the merged contributions.

Contributions:

- Created the initial repository.
- Established the team project structure.
- Defined work allocation and intermediate milestones.
- Created task-issue and pull-request templates.
- Documented the collaboration workflow.
- Defined the shared chronological evaluation protocol.
- Added the frozen district-boundary snapshot and metadata.
- Developed the request-to-district assignment function.
- Built the continuous district-week panel.
- Implemented shared lag and rolling-history features.
- Developed the previous-week baseline.
- Developed the four-week-average baseline.
- Developed Poisson regression forecasting.
- Compared 2018 and 2020 training-window starts.
- Produced district-level validation metrics.
- Generated validation predictions and figures.
- Added leakage and weekly-grid tests.
- Created the forecasting notebook and documentation.
- Added the run manifest.
- Integrated and merged teammate pull requests #1–#4.

Primary files:

```text
README.md
CONTRIBUTING.md
.github/
data/README.md
data/reference/
src/demand_forecasting.py
tests/test_demand_forecasting.py
notebooks/05_demand_forecasting/
results/demand_forecasting/
reports/figures/demand_forecasting/
requirements-forecasting.txt
```

Main result:

- The Poisson model trained on 2020–2023 achieved MAE 13.643 and RMSE 19.132.
- This is the strongest result currently merged into `main`.

---

### Contribution Summary

| Member | Teammate | Primary responsibility | Repository status |
|---|---|---|---|
| Member 1 | Abhijith Reddy | Data preparation and cleaning | Merged into `main` |
| Member 2 | Haritha Gottumukkala | EDA, map verification, and feature engineering | Merged into `main` |
| Member 3 | Divija Puli | Random Forest forecasting | Merged into `main` |
| Member 4 | Xinghan Chen | XGBoost forecasting and error analysis | Completed on remote branch; not merged |
| Member 5 | Srinidhi Jaya Revanth Srirangarajapally | Shared Poisson forecasting and integration | Merged into `main` |

### Contribution verification note

Git history verifies ownership of the committed components described above.

Git history cannot independently verify:

- Hours worked.
- Informal discussions.
- Uncommitted assistance.
- Reviews conducted outside GitHub.
- Work stored only in external documents.

Those activities should be recorded separately if required for individual course reports.

---

## Repository Structure

```text
.
├── .github/
│   ├── ISSUE_TEMPLATE/
│   └── pull_request_template.md
├── data/
│   ├── raw/
│   ├── processed/
│   ├── reference/
│   └── README.md
├── notebooks/
│   ├── 01_data_preparation/
│   ├── 02_eda_features/
│   ├── 03_classification/
│   ├── 04_resolution_regression/
│   └── 05_demand_forecasting/
├── reports/
│   └── figures/
├── results/
│   ├── demand_forecasting/
│   ├── member2/
│   └── member3_random_forest/
├── src/
│   ├── data_preparation.py
│   ├── demand_forecasting.py
│   ├── eda_features.py
│   └── feature_comparison.py
├── tests/
│   ├── test_demand_forecasting.py
│   ├── test_eda_features.py
│   └── test_feature_comparison.py
├── CONTRIBUTING.md
├── requirements-forecasting.txt
└── README.md
```

Member 4’s XGBoost files are located on the unmerged branch and therefore are not present in the current `main` working tree.

---

## Installation

### Clone the repository

```bash
git clone https://github.com/Revanth0211/data245-san-jose-311-ml.git
cd data245-san-jose-311-ml
```

### Create a shared forecasting environment

Python 3.11 is recommended for the merged forecasting, EDA, and feature-engineering components.

```bash
python3.11 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements-forecasting.txt
```

On Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements-forecasting.txt
```

Member 4’s XGBoost work has a separate dependency file. The XGBoost dependencies should be installed in a separate virtual environment.

---

## Reproduction Instructions

Run all commands from the repository root.

### 1. Run the shared tests

```bash
python -m unittest discover -s tests -v
```

The current merged-main suite contains 25 tests.

### 2. Optionally rebuild the cleaned dataset

A cleaned dataset is already committed. To rebuild it using the current official source:

```bash
python src/data_preparation.py \
  --years 2018 2019 2020 2021 2022 2023 2024 2025
```

This command accesses the external CKAN API and rewrites generated files under `data/processed/`.

Current source files may differ from the source snapshot used for the committed results.

### 3. Build the shared district-week panel

```bash
python src/demand_forecasting.py
```

This creates:

```text
data/processed/district_week_development.csv
```

It also regenerates shared metrics and figures.

The generated district-week file is ignored by Git but is required by the Random Forest and XGBoost components.

### 4. Run the Random Forest analysis

Run the shared forecasting pipeline first, then execute:

```bash
python notebooks/03_classification/random_forest_forecasting.py
```

### 5. Run the EDA and feature notebooks

Run these notebooks in order:

```text
notebooks/02_eda_features/01_district_map_verification.ipynb
notebooks/02_eda_features/02_exploratory_data_analysis.ipynb
notebooks/02_eda_features/03_feature_engineering.ipynb
notebooks/02_eda_features/04_feature_comparison.ipynb
```

The committed notebooks contain no saved execution errors.

### 6. Run the shared forecasting notebook

```text
notebooks/05_demand_forecasting/weekly_demand_forecasting.ipynb
```

### 7. Access the Member 4 XGBoost work

Member 4’s work must first be merged or checked out from the remote branch:

```bash
git switch --track origin/Xinghan/xgboost-demand-forecasting
```

Then follow:

```text
notebooks/04_resolution_regression/README.md
```

Member 4 uses a separate dependency environment.

---

## Testing

The merged test suite verifies:

- Weekly-grid continuity.
- Correct lag values.
- Correct rolling means.
- Correct rolling standard deviations.
- Separation of district histories.
- Prevention of current-target leakage.
- Prevention of future-data leakage.
- Correct handling of year boundaries.
- Exclusion of split-crossing weeks.
- Exclusion of 2025 evaluation rows.
- Preservation of district-week keys and targets.
- Compatibility with shared feature definitions.
- Consistent training rows across feature experiments.
- Consistent validation rows across feature experiments.
- Training-only preprocessing.
- Finite predictions.
- Non-negative predictions.
- Explicit acceptance of provisional assumptions.
- Preservation of teammate forecasting artifacts.

Run:

```bash
python -m unittest discover -s tests -v
```

After regenerating notebooks or model outputs, check:

```bash
git status --short
git diff --check
```

Review generated changes before committing.

---

## Generated Outputs

### Member 1 data preparation

```text
data/processed/illegal_dumping_cleaned.csv
data/processed/source_manifest.csv
data/processed/cleaning_counts.csv
data/processed/data_dictionary.csv
results/member1_cleaning_summary.csv
```

### Member 2 EDA and feature comparison

```text
results/member2/feature_comparison_metrics.csv
results/member2/feature_comparison_predictions.csv
reports/figures/member2/feature_comparison.png
```

### Member 3 Random Forest

```text
results/member3_random_forest/random_forest_feature_removal_metrics.csv
results/member3_random_forest/random_forest_validation_predictions.csv
reports/figures/member3_random_forest/random_forest_feature_removal.png
```

### Member 4 XGBoost branch

```text
results/member4_xgboost/
reports/figures/member4_xgboost/
```

These paths are available on the Member 4 branch and are not currently merged into `main`.

### Member 5 shared forecasting

```text
results/demand_forecasting/validation_metrics.csv
results/demand_forecasting/validation_predictions.csv
results/demand_forecasting/district_metrics.csv
results/demand_forecasting/location_audit.csv
results/demand_forecasting/run_manifest.json
reports/figures/demand_forecasting/validation_timeseries.png
reports/figures/demand_forecasting/district_mae.png
```

---

## Limitations

1. **Reported demand is not incident prevalence.**  
   Multiple reports may describe one event, and some events may never be reported.

2. **Source coverage is not fully proven.**  
   Having data for every date does not guarantee complete coverage of every reporting channel.

3. **Zero-filled weeks are provisional.**  
   A missing district-week is treated as zero only when coverage is assumed to be complete.

4. **District geography is retrospective.**  
   A single current/2021-redistricting boundary snapshot is applied to all historical years.

5. **Some requests are geographically excluded.**  
   A total of 463 development-period requests do not fall inside the saved district polygons.

6. **Upstream coordinate exclusions remain unchanged.**  
   The cleaning pipeline excludes 1,071 records under its documented quality rules.

7. **Timestamp semantics require confirmation.**  
   Naive creation timestamps are provisionally treated as San José local wall-clock time.

8. **`Date Last Updated` is not a verified completion field.**  
   It should not be used as a closure timestamp without official documentation.

9. **2024 is development validation.**  
   Repeated comparisons on 2024 may influence model-selection decisions.

10. **2025 remains reserved.**  
    No current result reports final 2025 performance.

11. **Feature importance is not causal evidence.**  
    Model importance values do not explain why reports occur.

12. **District comparisons are not population-adjusted.**  
    Counts do not control for population, land area, land use, service access, or reporting behavior.

13. **Prediction intervals are not provided.**  
    The current models produce point predictions without calibrated uncertainty intervals.

---

## Current Project Status

### Completed and merged into `main`

- Data-download and cleaning pipeline.
- Cleaned 2018–2025 request-level dataset.
- Council-district boundary snapshot.
- District-map verification.
- Exploratory data analysis.
- Leakage-safe shared features.
- Continuous district-week panel construction.
- Previous-week baseline.
- Four-week-average baseline.
- Poisson regression.
- Poisson feature comparison.
- Random Forest feature-removal experiments.
- Shared tests, metrics, predictions, figures, and documentation.

### Completed but not merged into `main`

- XGBoost demand forecasting.
- XGBoost feature-set comparison.
- District-specific error analysis.
- Busy-week error analysis.
- Feature-importance analysis.
- Member 4 tests, notebook, figures, results, and environment specification.

### Remaining project decisions

- Confirm annual source completeness.
- Approve or revise the zero-fill convention.
- Confirm timezone and timestamp semantics.
- Approve fixed retrospective district geography.
- Decide whether historical-boundary sensitivity analysis is needed.
- Review unmatched and excluded coordinates.
- Review and merge Member 4’s XGBoost branch.
- Freeze the final model and evaluation protocol.
- Evaluate 2025 only after the protocol is frozen.
- Add a repository license if the project will be distributed publicly.

---

## Collaboration

See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow.

Each team contribution should document:

- Owner.
- Deliverable.
- Data and dependency versions.
- Reproduction command.
- Target definition.
- Feature definitions.
- Training and evaluation periods.
- Metrics.
- Figures.
- Assumptions.
- Limitations.
- Reviewer and review evidence.

Contribution should be evaluated using substantive deliverables, reproducibility, analysis, tests, documentation, review, and integration—not commit count alone.

