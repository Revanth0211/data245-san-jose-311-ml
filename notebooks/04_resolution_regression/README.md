# Member 4 — XGBoost weekly-demand fallback (intermediate milestone)

**Owner:** Member 4. **Status:** provisional, **2025 test not evaluated**.

This directory implements the team-agreed fallback to **XGBoost for weekly illegal-dumping report-demand forecasting**, plus district-specific and high-demand-week error diagnostics. The original closure-time regression is not feasible without a verified case-closure timestamp; the source's `date_last_updated` is not an established closure time.

## What is independent work?

| Component | Owner / reuse |
|---|---|
| Cleaned 311 cases | Member 1; read only |
| Shared district-week counts, lag history, Poisson and simple baselines | Member 5; read only |
| Additional lag/rolling feature functions | Member 2, optional; imported from `src/eda_features.py` |
| **XGBoost regression, feature-set comparison, district and busy-week diagnostics** | **Member 4 (this folder)** |

**No teammate source modules are copied or modified in this contribution.** All experiments use Member 5's shared panel, rather than regenerating district assignments or weekly count targets. `--with-member2` requires `src/eda_features.py` to be present in the local checkout.

## Reproduce on Windows PowerShell

Open PowerShell at the project root (containing `src`, `data`, `notebooks`, and `results`):

```powershell
python -m pip install -r requirements-forecasting.txt
python -m pip install -r notebooks/04_resolution_regression/requirements_member4.txt
python -m unittest discover -s notebooks/04_resolution_regression -p test_member4_xgboost.py -v
python notebooks/04_resolution_regression/member4_xgboost.py --provisional --with-member2
```

The command above is the **recommended run** when `src/eda_features.py` is available. It runs all three feature combinations and uses `member2_lags` consistently for district/busy-week diagnostics and all focused plots. If Member 2's module is not yet present, run this **shared-only fallback** instead:

```powershell
Test-Path .\src\eda_features.py
python notebooks/04_resolution_regression/member4_xgboost.py --provisional
```

Open `notebooks/04_resolution_regression/member4_xgboost_analysis.ipynb` in VS Code with an installed Python/Jupyter kernel, and **Run All**. The first code cell loads `member4_xgboost.py` from the repository and checks its interface version. It automatically runs the shared model and, if Member 2's module exists, the additional two feature sets; in that case, **member2_lags is the primary error-analysis model**. The notebook, saved district and busy-week charts, citywide weekly plot, and feature-importance plot all use that same model. Running the shared-only command later will regenerate these charts for `shared`, so rerun with `--with-member2` before committing your main analysis results. Saved notebook output is a development snapshot; rerun it after shared data or feature changes.

If `data/processed/district_week_development.csv` is missing, run `python src/demand_forecasting.py` to generate it from the shared source data and district polygons. This may also regenerate Member 5 result files; do not include unrelated generated changes in the Member 4 PR. **Do not** train on `results/demand_forecasting/validation_predictions.csv`, which only contains validation predictions and is used here as a row-alignment check.

## Frozen evaluation protocol

- **Prediction target:** count of retained reports received in a district during one complete Monday–Sunday week. One row = one district-week.
- **History:** 2018–2019 counts may contribute to past-only features; not model training.
- **Training:** complete 2020–2023 weeks (2,080 rows in current shared panel).
- **Validation:** complete 2024 weeks from Jan 1 through Dec 23 (520 rows, ten districts × 52 weeks).
- **Holdout:** **2025 is never loaded/evaluated**. Exclude the Dec 30, 2024–Jan 5, 2025 cross-boundary week.
- **Validation method:** fixed trained estimator, evaluated one week ahead using *observed completed earlier weeks* to make lags. This is rolling one-week-ahead assessment, not a year-long forecasting simulation starting Jan 1.
- **Preprocessing:** district one-hot encoding trained on training data only. XGBoost configuration is fixed, without hyperparameter search. Prediction values are clipped at zero to avoid negative count forecasts.
- **MAE/RMSE:** errors in reports per district-week, with identical scoring keys/targets as the Poisson 2020 comparison (checked against the teammate's existing `validation_predictions.csv` if present).

Feature sets:

- `shared`: Member 5's seven numeric forecasting features plus district identity (reference and fallback, requires no Member 2 code).
- `member2_lags`: Member 2's calendar variables and lag 1/2/4/8 features plus district identity (**primary when `--with-member2` is enabled**).
- `member2_full`: those calendar/lag features and six historical rolling / change features plus district identity (optional).

**Primary-analysis consistency:** the CLI accepts `--primary-experiment shared|member2_lags|member2_full` for an explicit reporting focus, provided that feature set was trained. By default `member2_lags` is the primary when available, otherwise `shared`. All detailed graphs and group metrics in the Notebook are filtered to the same primary model; the comparison table still retains every model. This is a *2024 development analysis decision*, not a held-out test selection.

**Only pre-existing, historically available variables are features.** The 2024 observed count is used as a validation label and **only after prediction** to identify busy weeks for descriptive error analysis.

Busy-week rules, *declared using 2020–2023 training observations*:

- `busy_district_week`: actual 2024 count is at least that district's training-period 90th percentile. This is post-hoc, not a feature or real-time busy forecast.
- `busy_citywide_week`: actual sum over all ten districts is at least the training-period 90th percentile of weekly citywide sums. Group diagnostics continue reporting per district-week MAE/RMSE.

## Measured provisional 2024 validation results

Results reproduced locally on the shared 2024 validation panel (2020–2023 training; fixed hyperparameters):

| XGBoost feature set | Training rows | Validation rows | MAE | RMSE |
|---|---:|---:|---:|---:|
| Shared | 2,080 | 520 | 14.171 | 20.325 |
| Member 2 calendar + lags | 2,080 | 520 | 13.942 | 20.195 |
| Member 2 full feature set | 2,080 | 520 | 14.007 | 20.356 |

Member 5's **Poisson model trained on 2020–2023** yields MAE **13.643**, RMSE **19.132**. XGBoost beats the previous-week and four-week-average baselines on this validation set, but does **not** beat Poisson here. The small differences among XGBoost feature sets should not be oversold; no formal uncertainty test has been performed.

**Primary `member2_lags` XGBoost diagnostics:** District 3 has the largest MAE, **31.81** reports per district-week. Under the declared post-hoc district-busy threshold, 123 validation district-weeks are busy (MAE **23.42**, mean prediction bias **−22.19**), while 397 are nonbusy (MAE **11.01**). This reveals underprediction on observed high-demand weeks, not causality or the ability to predict busy weeks in advance. The shared reference retains its own metrics separately in the CSV files.

Metrics remain **provisional** because source coverage, zero-fill convention and application of the fixed, retrospectively mapped district boundaries still require team confirmation. Changes to the shared panel can change all results; regenerate outputs after changes, and record the manifest's panel hash.

## Generated outputs

- `results/member4_xgboost/validation_metrics.csv` — one summary row per XGBoost feature set.
- `results/member4_xgboost/validation_predictions.csv` — observed / predicted / error for each scored district-week, with *post-hoc* labels.
- `results/member4_xgboost/district_metrics.csv` — per-district MAE/RMSE and signed bias.
- `results/member4_xgboost/busy_week_metrics.csv` — busy vs nonbusy district-week MAE/RMSE.
- `results/member4_xgboost/citywide_busy_week_metrics.csv` — descriptive citywide busy-week breakdown.
- `results/member4_xgboost/feature_importance.csv` — XGBoost importance scores; not causal.
- `results/member4_xgboost/run_manifest.json` — data SHA256, parameter protocol, package versions, limitations, row-identity check.
- `reports/figures/member4_xgboost/` — five PNG charts of comparisons, districts, busy-week errors, citywide patterns, feature importance.
- `notebooks/04_resolution_regression/member4_xgboost_analysis.ipynb` — executed walkthrough with interpretation.
- `notebooks/04_resolution_regression/test_member4_xgboost.py` — seventeen unit tests, including an end-to-end manifest/Notebook contract regression test (including primary-model consistency checks).

For a clean PR, stage only this Member 4 directory, `results/member4_xgboost/`, and `reports/figures/member4_xgboost/`. Do not commit generated shared data, teammate result files, ZIPs, caches, or 2025 evaluation outputs.
