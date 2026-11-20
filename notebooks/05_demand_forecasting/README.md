# Weekly demand forecasting

**Contributor:** Srinidhi Jaya Revanth Srirangarajapally

This guide covers the development experiment. The [final evaluation](FINAL_HANDOFF.md) documents the refit and held-out results.

## Reproduce

From the repository root, create a Python environment and install `requirements-forecasting.txt`. Run:

```sh
python -m unittest discover -s tests -v
python src/demand_forecasting.py
```

Input: `data/processed/illegal_dumping_cleaned.csv` from Member 1's merged PR. The archived official geometry and metadata are in `data/reference/`. The run manifest records input and geometry SHA-256 hashes. Generated weekly data and unmatched request IDs remain in ignored `data/processed/`; small metric tables and figures are in `results/demand_forecasting/` and `reports/figures/demand_forecasting/`.

## Target and forecast protocol

The target is the number of retained, uniquely mapped illegal-dumping reports created in each district during a complete Monday–Sunday week. This measures reported demand, not the true number of dumping incidents. Requests excluded upstream or outside the archived polygons are not counted; inspect `location_audit.csv` before interpretation.

At the start of each week, predict that week's count using actual counts from already completed weeks. The fitted model remains fixed throughout 2024. This is rolling one-week-ahead evaluation, not a forecast of all of 2024 made in January. No current-week status, update timestamp, or future count is used as a feature.

Features: district identity, counts from 1, 2, and 4 weeks earlier, shifted 4- and 13-week means, and sine/cosine annual calendar terms. Lags are computed independently within districts on a continuous weekly grid. The first 13 weeks are warm-up history and cannot be scored. Historical 2018–2019 observations can supply lag history for the 2020 training-window experiment.

## Evaluation agreement

Compare training starts of 2018 and 2020, ending in 2023, on exactly the same 2024 validation district-weeks. Every district for a week stays in the same split. Scaling and district encoding are fitted on training rows only. The Poisson model uses fixed alpha=1; no hyperparameter search has been performed. Both baselines are evaluated on the identical rows. MAE and RMSE are in requests per district-week; the plotted citywide totals are descriptive, not the pooled district-level metric.

The last validation week began December 23, 2024. The week beginning December 30 crossed the year boundary. The separate final evaluator scored 51 complete weeks in 2025.

## Dependencies and limitations

### Measured provisional results

Across 520 validation district-weeks, previous-week MAE/RMSE are 15.804/22.271; four-week-average MAE/RMSE are 15.030/20.714. Poisson trained from 2018 achieves 13.843/19.415, while Poisson trained from 2020 achieves 13.643/19.132. The latter reduces MAE by approximately 9.23% relative to the four-week baseline. The difference between training windows is small (about 0.20 requests in MAE), so this is evidence for the existing 2020 start in this experiment, not a universal rule to discard older history. Both charts compare the two baselines with the 2020-start Poisson experiment.

Of 181,326 cleaned development-period requests, 180,863 map uniquely to the archived districts; 463 fall outside all polygons and are excluded from district counts. No multiple matches occurred. Upstream exclusions are additional. These geography exclusions and the unconfirmed coverage assumptions limit interpretation.

The first execution exposed numerical warnings with NumPy 2.0.2 on this machine. The pinned NumPy 1.26.4 environment reproduced the same scores with runtime warnings treated as errors. Leakage tests and fresh-kernel notebook execution are part of the verification.

The final run treated timestamps as local wall-clock times and used a fixed district map retrospectively. Source completeness and zero filling remain assumptions. The [protocol](../../config/final_evaluation_protocol.json) records the coordinate exclusions and geographic conventions.

## AI assistance

AI assistance supported implementation, tests, explanations and experiment documentation.

## Sources

- City 311 data: https://data.sanjoseca.gov/dataset/311-service-request-data
- Official district layer: https://geo.sanjoseca.gov/server/rest/services/PLN/PLN_AdministrativeBoundaries/MapServer/1
- Poisson model reference: https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.PoissonRegressor.html
