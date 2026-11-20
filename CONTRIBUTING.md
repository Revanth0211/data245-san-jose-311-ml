# Contributions and reproducibility

The [project overview](README.md#team-contributions) identifies all five contributors and links each person’s analysis to the recorded results.

## How the work fits together

Abhijith Reddy prepared and audited the cleaned request records. Haritha Gottumukkala verified the district geography and evaluated shared features. Divija Puli and Xinghan Chen used district-week observations to compare Random Forest and XGBoost configurations and examine forecast errors. Srinidhi Jaya Revanth Srirangarajapally built the shared weekly forecasting pipeline and reconciled the model predictions on common validation rows.

## Reviewing a result

1. Identify the evaluation period. The [2024 comparison](results/forecasting_presentation/model_comparison.csv) covers model development. The [2025 metrics](results/demand_forecasting_final/test_metrics.csv) cover the frozen Poisson and baseline test.
2. Use district, week start and observed count to align predictions before comparing errors. The [final prediction table](results/demand_forecasting_final/test_predictions.csv) records each scored forecast.
3. Consult the [data guide](data/README.md) and [frozen protocol](config/final_evaluation_protocol.json) for exclusions, input conventions and model settings.

For maintenance, document the affected analysis, run the relevant tests and link the resulting evidence in the pull request. Keep request-level downloads and generated local datasets outside version control.
