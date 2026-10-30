# DATA 245: San Jose 311 Illegal Dumping Prediction

Shared code and reproducible analysis for the ML group project.

**Intermediate milestone:** a checked dataset, initial exploration, and baseline plus first-model validation results for each feasible prediction task. This repository currently contains the collaboration structure; project analysis and measured results are still to be added.

[Team agenda and intermediate to-do](https://docs.google.com/document/d/1_RpHXCC9rbM1_7NOeakiumGHvwNwSP7YVNQFZK5dJ3I/edit) · [Contribution workflow](CONTRIBUTING.md)

## Work split

Replace Member 1–4 with the ML teammates' names after the team confirms ownership.

| Owner | Work folder | Deliverables for the intermediate milestone |
| --- | --- | --- |
| Member 1: data preparation | `notebooks/01_data_preparation/` | Cleaning code, data dictionary, source/coverage audit, record counts, and cleaned-data handoff. |
| Member 2: EDA and shared features | `notebooks/02_eda_features/` | Temporal and district analysis, 4–6 interpreted charts, shared feature code, and closure-data feasibility findings. |
| Member 3: slow-resolution classification | `notebooks/03_classification/` | Valid label rules, sample/class counts, majority baseline, initial logistic regression, confusion matrix, and validation analysis. Conditional on reliable completion outcomes. |
| Member 4: resolution-time regression | `notebooks/04_resolution_regression/` | Valid duration rules, sample/exclusion counts, training-median baseline, one simple regression model, and validation errors in days. Conditional on reliable completion outcomes. |
| Revanth: weekly demand forecasting | `notebooks/05_demand_forecasting/` | District-week table, past-only lag/rolling features, previous-week and four-week-average baselines, initial Poisson regression, and district-level validation errors. |

If completion outcomes are unreliable, Member 3 takes Random Forest demand forecasting and feature-removal experiments; Member 4 takes XGBoost demand forecasting and district/busy-week error analysis. Use the shared weekly table and common evaluation setup. `Date Last Updated` alone does not establish completion.

## When Revanth's work starts

Start now with literature reading, a proposed district-week schema, forecast-date definitions, and aggregation/feature/baseline code. A small sample can be used to check the pipeline, but sample or synthetic results must be identified as such.

Ask Member 1 for an early cleaned sample containing request ID, creation date/time, and district or usable coordinates, together with known coverage gaps. Confirm one archived district boundary layer and local-time handling with Members 1 and 2. Full dataset cleaning and forecasting development can then continue in parallel.

Run reportable baselines and Poisson regression once complete district-week counts and coverage checks are available. Calendar-based features use the forecast week; historical count features use only completed earlier weeks.

## Repository layout

```text
data/                 Data instructions and local raw/processed data
notebooks/            Member-owned exploratory and modeling notebooks
src/                  Reusable cleaning, features, training, and evaluation code
results/              Small, reproducible metric tables and experiment summaries
reports/figures/      Figures used in individual reports and group discussions
.github/              Task and pull-request templates
```

Raw data and generated processed datasets stay outside version control. Share source URLs, acquisition dates, cleaning steps, schemas, and reproducible download instructions in `data/README.md`. Small metric tables and figures may be committed.

## Shared evaluation agreement

- Planned development period: 2020–2023; initial validation: 2024, subject to verified source coverage.
- Reserve 2025 for final testing. Keep all districts from a given week in the same chronological split.
- Fit preprocessing on training data. Exclude features that use information unavailable at prediction time.
- Within each task, compare models on the same eligible rows and validation period.
- Classification: precision, recall, F1, and confusion matrix. Resolution-time regression and demand forecasting: MAE and RMSE. Scores across different targets are interpreted separately.
- Forecast complete Monday–Sunday weeks. Fill missing counts with zero only where source coverage is verified; distinguish missing coverage from zero demand.

## Collaboration and fair contribution

Each member works from their own GitHub account, owns a substantial reproducible component, and reviews another member's work. Use a task issue to record the owner, estimated effort, due date, deliverable, evidence link, and status. Explicitly assign integration and debugging effort too.

Submit changes through a branch and pull request. Include what changed, evidence or figures, how to reproduce it, difficulties, and remaining work. See [CONTRIBUTING.md](CONTRIBUTING.md). Commit counts alone do not measure contribution fairly; use completed deliverables, analysis, reviews, and integration work.

## Individual status reports

Each member submits at least three pages excluding references, focused on their own progress, findings, difficulties and planned fixes, and remaining tasks. Each person individually reviews at least 13 relevant research papers from reputed conferences/journals, synthesizes them in their own words, and uses APA citations. The final report's literature-review section should be complete at the intermediate stage.

Baseline plus initial-model completion is the team's proposed milestone; the supplied rubric does not mandate a specific number of trained models.

## Adding teammates

The repository owner can invite teammates at **Settings → Collaborators → Add people**. Invite each member by GitHub username or email. After accepting, they can clone the private repository and contribute. A repository link alone does not grant access.

```bash
git clone https://github.com/Revanth0211/data245-san-jose-311-ml.git
cd data245-san-jose-311-ml
```

The team should agree on the Python version and record dependencies when implementation starts. No trained models or project results are included in this initial setup.
