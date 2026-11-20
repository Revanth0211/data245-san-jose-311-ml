# Forecasting San José 311 illegal-dumping reports

How many new illegal-dumping reports will each of San José’s ten council districts receive next week? The team used City of San José 311 records from 2018–2025 to study reported demand. Creation timestamps support a weekly arrivals target. The available records did not establish when requests were completed.

## Team contributions

| Contributor | Work | Evidence |
|---|---|---|
| Abhijith Reddy (Member 1) | **Data preparation.** Harmonized annual exports, filtered illegal-dumping requests, deduplicated records and audited exclusions. | [Methods](notebooks/01_data_preparation/README.md) · [Results](results/member1_cleaning_summary.csv) |
| Haritha Gottumukkala (Member 2) | **Geography, EDA and features.** Verified district assignments, analyzed temporal patterns and compared Poisson feature sets on identical weeks. | [Methods](notebooks/02_eda_features/README.md) · [Results](results/member2/final_report_evidence/EVIDENCE_SUMMARY.md) |
| Divija Puli (Member 3) | **Random Forest.** Compared feature sets and analyzed district errors and large underpredictions. | [Methods](notebooks/03_classification/FINAL_PRESENTATION_MEMBER3.md) · [Results](results/member3_random_forest/random_forest_feature_removal_metrics.csv) |
| Xinghan Chen (Member 4) | **XGBoost.** Compared boosted-tree configurations and measured how errors changed across districts and busy weeks. | [Methods](notebooks/04_resolution_regression/README.md) · [Results](results/member4_xgboost/busy_week_metrics.csv) |
| Srinidhi Jaya Revanth Srirangarajapally (Member 5) | **Weekly forecasting and integration.** Built the shared weekly panel, evaluated Poisson and two baselines, aligned team validation predictions and ran the frozen 2025 evaluation. | [Methods](notebooks/05_demand_forecasting/FINAL_HANDOFF.md) · [Results](results/demand_forecasting_final/test_metrics.csv) |

## Forecast design

Each observation represents one district and one complete Monday–Sunday week. The pipeline assigns coordinates to an archived council district, counts requests by creation week and builds predictors using only completed weeks. The shared Poisson model combines district identity, annual seasonality, counts from one, two and four weeks earlier, and four- and thirteen-week trailing averages.

Development compared training windows starting in 2018 and 2020. The selected window used 2020–2023 for training and 2024 for validation. The final Poisson fit used 2,600 district-weeks from 2020–2024. During testing, its coefficients stayed fixed and each forecast could use the observed counts from completed prior weeks.

## Results

Errors are reports per district-week. Lower values indicate smaller errors.

| Forecast | 2024 validation MAE | 2024 validation RMSE | 2025 test MAE | 2025 test RMSE |
|---|---:|---:|---:|---:|
| Previous week | 15.80 | 22.27 | 13.97 | 19.07 |
| Four-week average | 15.03 | 20.71 | 12.95 | **17.25** |
| Shared Poisson | **13.64** | **19.13** | **12.59** | 17.53 |
| Poisson feature comparison, with lags | 13.85 | 19.48 | — | — |
| Random Forest, without rolling averages | 14.03 | 20.11 | — | — |
| XGBoost, with historical lags | 13.94 | 20.20 | — | — |

All six configurations were compared on the same 520 district-weeks in 2024. Dashes mark configurations evaluated only during validation. The 2025 test covered 510 district-weeks, with Monday start dates from January 6 through December 22. The weeks crossing the year boundaries were excluded from scoring. Poisson reduced test MAE by about 2.8% relative to the four-week average. The four-week average had the lowest RMSE. [Validation comparison](results/forecasting_presentation/model_comparison.csv) · [Test scores](results/demand_forecasting_final/test_metrics.csv) · [District-level test results](results/demand_forecasting_final/district_metrics.csv)

## Reproducing the analysis

From the repository root, install the shared dependencies and run the unit tests:

```sh
python -m pip install -r requirements-forecasting.txt
python -m unittest discover -s tests -v
```

The [data guide](data/README.md) describes the source files and cleaning procedure. The methods links above lead to each contributor’s notebooks, commands and environment notes. XGBoost uses its own [dependency file](notebooks/04_resolution_regression/requirements_member4.txt). To reconstruct the development comparison from committed predictions, run `python src/forecasting_summary.py`. The [final run manifest](results/demand_forecasting_final/run_manifest.json) records the evaluation settings, software versions and prediction checksum.

## Interpretation and limitations

311 volume reflects reporting behavior and service access as well as dumping activity. The analysis treats creation timestamps as local wall-clock time, uses a fixed district map retrospectively and excludes reports without a unique district match. Zero-filled weeks assume complete source coverage. These conventions were frozen for evaluation; source completeness and historical boundary validity were not independently verified. [Evaluation protocol](config/final_evaluation_protocol.json) · [Location audit](results/demand_forecasting_final/location_audit.csv)
